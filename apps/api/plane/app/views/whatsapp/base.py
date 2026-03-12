import logging

from django.conf import settings
from django.db.models import Exists, OuterRef
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from plane.app.views.base import BaseAPIView
from plane.db.models import WhatsAppMessage
from plane.utils.evolution_client import EvolutionAPIClient

logger = logging.getLogger("plane.api")


def _get_client() -> EvolutionAPIClient:
    if not getattr(settings, "EVOLUTION_API_URL", ""):
        raise ValueError("Evolution API not configured")
    return EvolutionAPIClient()


class WhatsAppStatusEndpoint(BaseAPIView):
    """GET connection status of the WhatsApp instance."""

    def get(self, request):
        try:
            client = _get_client()
            state = client.get_connection_state()
            instance_state = state.get("instance", {}).get("state", "close")
            return Response({
                "state": instance_state,
                "instance": settings.EVOLUTION_INSTANCE_NAME,
            })
        except ValueError:
            return Response(
                {"state": "error", "detail": "Evolution API not configured"},
                status=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.exception("WhatsApp status error: %s", e)
            return Response(
                {"state": "error", "detail": "Connection error"},
                status=http_status.HTTP_502_BAD_GATEWAY,
            )


class WhatsAppQREndpoint(BaseAPIView):
    """GET QR code for pairing WhatsApp."""

    def get(self, request):
        try:
            client = _get_client()
            result = client.connect_instance()
            return Response(result)
        except ValueError:
            return Response(
                {"detail": "Evolution API not configured"},
                status=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.exception("WhatsApp QR error: %s", e)
            return Response(
                {"detail": "Connection error"},
                status=http_status.HTTP_502_BAD_GATEWAY,
            )


class WhatsAppDisconnectEndpoint(BaseAPIView):
    """POST to disconnect WhatsApp instance."""

    def post(self, request):
        try:
            client = _get_client()
            client.logout_instance()
            return Response({"detail": "Disconnected"})
        except ValueError:
            return Response(
                {"detail": "Evolution API not configured"},
                status=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.exception("WhatsApp disconnect error: %s", e)
            return Response(
                {"detail": "Connection error"},
                status=http_status.HTTP_502_BAD_GATEWAY,
            )


class WhatsAppSendEndpoint(BaseAPIView):
    """POST to send a WhatsApp message."""

    def post(self, request, slug):
        try:
            client = _get_client()
        except ValueError:
            return Response(
                {"detail": "Evolution API not configured"},
                status=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        phone = request.data.get("phone", "")
        message_text = request.data.get("message", "")
        contact_name = request.data.get("contact_name", "")
        message_type = request.data.get("message_type", "TEXT")

        if not phone or not message_text:
            return Response(
                {"detail": "phone and message are required"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        from plane.db.models import Workspace

        workspace = Workspace.objects.filter(slug=slug).first()

        msg = WhatsAppMessage.objects.create(
            workspace=workspace,
            phone=phone,
            contact_name=contact_name,
            direction=WhatsAppMessage.Direction.OUTBOUND,
            message_type=message_type,
            content=message_text,
            status=WhatsAppMessage.Status.PENDING,
            sent_by=request.user,
        )

        try:
            result = client.send_text(phone, message_text)
            msg.status = WhatsAppMessage.Status.SENT
            msg.evolution_message_id = result.get("key", {}).get("id", "")
            msg.save(update_fields=["status", "evolution_message_id"])
            return Response(_serialize_message(msg), status=http_status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("WhatsApp send error: %s", e)
            msg.status = WhatsAppMessage.Status.FAILED
            msg.error_detail = str(e)[:500]
            msg.save(update_fields=["status", "error_detail"])
            return Response(
                {"detail": "Failed to send message", "id": str(msg.id)},
                status=http_status.HTTP_502_BAD_GATEWAY,
            )


class WhatsAppResendEndpoint(BaseAPIView):
    """POST to resend failed messages."""

    def post(self, request, slug):
        try:
            client = _get_client()
        except ValueError:
            return Response(
                {"detail": "Evolution API not configured"},
                status=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        message_ids = request.data.get("message_ids", [])
        if not message_ids:
            return Response(
                {"detail": "message_ids required"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        from plane.db.models import Workspace

        workspace = Workspace.objects.filter(slug=slug).first()

        originals = WhatsAppMessage.objects.filter(
            id__in=message_ids,
            status=WhatsAppMessage.Status.FAILED,
            workspace=workspace,
        )

        results = {"sent": 0, "failed": 0, "errors": []}
        for original in originals:
            new_msg = WhatsAppMessage.objects.create(
                workspace=workspace,
                phone=original.phone,
                contact_name=original.contact_name,
                direction=WhatsAppMessage.Direction.OUTBOUND,
                message_type=original.message_type,
                content=original.content,
                status=WhatsAppMessage.Status.PENDING,
                sent_by=request.user,
                resent_from=original,
            )
            try:
                result = client.send_text(original.phone, original.content)
                new_msg.status = WhatsAppMessage.Status.SENT
                new_msg.evolution_message_id = result.get("key", {}).get("id", "")
                new_msg.save(update_fields=["status", "evolution_message_id"])
                results["sent"] += 1
            except Exception as e:
                new_msg.status = WhatsAppMessage.Status.FAILED
                new_msg.error_detail = str(e)[:500]
                new_msg.save(update_fields=["status", "error_detail"])
                results["failed"] += 1
                results["errors"].append({"phone": original.phone, "error": str(e)[:200]})

        return Response(results)


class WhatsAppMessagesEndpoint(BaseAPIView):
    """GET message history for a workspace."""

    def get(self, request, slug):
        from plane.db.models import Workspace

        workspace = Workspace.objects.filter(slug=slug).first()
        if not workspace:
            return Response([], status=http_status.HTTP_200_OK)

        resend_subquery = WhatsAppMessage.objects.filter(resent_from=OuterRef("pk"))
        qs = (
            WhatsAppMessage.objects.filter(workspace=workspace)
            .annotate(_has_been_resent=Exists(resend_subquery))
            .select_related("sent_by")
        )

        phone = request.query_params.get("phone")
        if phone:
            qs = qs.filter(phone__icontains=phone)
        msg_type = request.query_params.get("type")
        if msg_type:
            qs = qs.filter(message_type=msg_type)
        direction = request.query_params.get("direction")
        if direction:
            qs = qs.filter(direction=direction)
        msg_status = request.query_params.get("status")
        if msg_status:
            qs = qs.filter(status=msg_status)

        messages = qs[:200]
        return Response([_serialize_message(m) for m in messages])


class WhatsAppWebhookEndpoint(BaseAPIView):
    """POST webhook receiver for Evolution API events."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        webhook_key = getattr(settings, "EVOLUTION_API_GLOBAL_KEY", "")
        incoming_key = request.headers.get("apikey", "")
        if not webhook_key or incoming_key != webhook_key:
            return Response(
                {"error": "Unauthorized"},
                status=http_status.HTTP_403_FORBIDDEN,
            )

        event = request.data.get("event", "")
        data = request.data.get("data", {})

        if event == "messages.upsert":
            key = data.get("key", {})
            if not key.get("fromMe", True):
                remote_jid = key.get("remoteJid", "")
                phone = remote_jid.replace("@s.whatsapp.net", "").replace("@g.us", "")
                content = (
                    data.get("message", {}).get("conversation", "")
                    or data.get("message", {}).get("extendedTextMessage", {}).get("text", "")
                )
                push_name = data.get("pushName", "")
                if phone and content:
                    WhatsAppMessage.objects.create(
                        phone=phone,
                        contact_name=push_name,
                        direction=WhatsAppMessage.Direction.INBOUND,
                        message_type=WhatsAppMessage.MessageType.TEXT,
                        content=content,
                        status=WhatsAppMessage.Status.DELIVERED,
                    )

        elif event == "messages.update":
            _process_status_update(data)

        return Response({"success": True})


def _process_status_update(data):
    STATUS_MAP = {
        "DELIVERY_ACK": WhatsAppMessage.Status.DELIVERED,
        "READ": WhatsAppMessage.Status.READ,
        "PLAYED": WhatsAppMessage.Status.READ,
    }
    items = data if isinstance(data, list) else [data]
    for item in items:
        msg_id = item.get("key", {}).get("id", "")
        update_status = item.get("status", "")
        new_status = STATUS_MAP.get(update_status)
        if msg_id and new_status:
            WhatsAppMessage.objects.filter(
                evolution_message_id=msg_id,
            ).exclude(
                status=WhatsAppMessage.Status.FAILED,
            ).update(status=new_status)


def _serialize_message(msg) -> dict:
    return {
        "id": str(msg.id),
        "phone": msg.phone,
        "contact_name": msg.contact_name,
        "direction": msg.direction,
        "direction_display": msg.get_direction_display(),
        "message_type": msg.message_type,
        "message_type_display": msg.get_message_type_display(),
        "content": msg.content,
        "status": msg.status,
        "status_display": msg.get_status_display(),
        "sent_by": str(msg.sent_by_id) if msg.sent_by_id else None,
        "sent_by_name": (
            msg.sent_by.display_name
            if msg.sent_by
            else None
        ),
        "evolution_message_id": msg.evolution_message_id,
        "error_detail": msg.error_detail,
        "resent_from": str(msg.resent_from_id) if msg.resent_from_id else None,
        "is_resend": msg.resent_from_id is not None,
        "has_been_resent": getattr(msg, "_has_been_resent", False),
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }
