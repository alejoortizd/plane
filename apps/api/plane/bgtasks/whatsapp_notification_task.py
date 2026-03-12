"""
Celery tasks for sending WhatsApp notifications via Evolution API.

Hooked into the existing Plane notification pipeline so users with
a mobile_number receive real-time WhatsApp messages on issue activity.
"""

import logging

from celery import shared_task
from django.conf import settings

from plane.db.models import User

logger = logging.getLogger("plane.worker")

FIELD_LABELS = {
    "state": "estado",
    "priority": "prioridad",
    "assignees": "asignados",
    "labels": "etiquetas",
    "target_date": "fecha límite",
    "start_date": "fecha inicio",
    "estimate_point": "estimación",
    "parent": "tarea padre",
    "name": "nombre",
    "comment": "comentario",
}


def _build_message(
    actor_name: str,
    issue_identifier: str,
    issue_name: str,
    project_name: str,
    activities: list[dict],
    sender_type: str,
) -> str | None:
    """Build a human-readable WhatsApp message from the activity list."""
    if not activities:
        return None

    parts = []
    for activity in activities:
        field = activity.get("field") or ""
        verb = activity.get("verb") or ""
        old_value = activity.get("old_value") or ""
        new_value = activity.get("new_value") or ""
        comment_text = activity.get("issue_comment") or ""

        if field == "description":
            continue

        if verb == "created" and not field:
            parts.append(
                f"*{actor_name}* creó la tarea "
                f"*{issue_identifier}: {issue_name}* "
                f"en el proyecto *{project_name}*."
            )
        elif field == "state":
            parts.append(
                f"La tarea *{issue_identifier}: {issue_name}* "
                f"cambió de estado: {old_value} → {new_value}."
            )
        elif field == "priority":
            parts.append(
                f"La tarea *{issue_identifier}: {issue_name}* "
                f"cambió de prioridad: {old_value or 'ninguna'} → {new_value or 'ninguna'}."
            )
        elif field == "assignees" and new_value:
            if sender_type == "in_app:issue_activities:assigned":
                parts.append(
                    f"*{actor_name}* te asignó la tarea "
                    f"*{issue_identifier}: {issue_name}* "
                    f"en el proyecto *{project_name}*."
                )
            else:
                parts.append(
                    f"Se actualizaron los asignados de "
                    f"*{issue_identifier}: {issue_name}*."
                )
        elif field == "comment":
            snippet = comment_text[:200] + "…" if len(comment_text) > 200 else comment_text
            parts.append(
                f"*{actor_name}* comentó en "
                f"*{issue_identifier}: {issue_name}*"
                + (f"\n_{snippet}_" if snippet else "")
            )
        elif field == "target_date":
            parts.append(
                f"*{issue_identifier}: {issue_name}* "
                f"cambió fecha límite: {old_value or 'sin fecha'} → {new_value or 'sin fecha'}."
            )
        elif field == "labels":
            parts.append(
                f"Se actualizaron las etiquetas de "
                f"*{issue_identifier}: {issue_name}*."
            )
        elif field:
            label = FIELD_LABELS.get(field, field)
            parts.append(
                f"*{issue_identifier}: {issue_name}* — "
                f"se actualizó _{label}_."
            )

    if not parts:
        return None

    return "\n\n".join(parts)


def _build_mention_message(
    actor_name: str,
    issue_identifier: str,
    issue_name: str,
    is_comment_mention: bool,
) -> str:
    if is_comment_mention:
        return (
            f"*{actor_name}* te mencionó en un comentario de "
            f"*{issue_identifier}: {issue_name}*."
        )
    return (
        f"*{actor_name}* te mencionó en la tarea "
        f"*{issue_identifier}: {issue_name}*."
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_whatsapp_notification(self, phone: str, message: str):
    """Send a single WhatsApp message via Evolution API."""
    if not getattr(settings, "EVOLUTION_API_URL", ""):
        return {"status": "skipped", "reason": "evolution_api_not_configured"}

    try:
        from plane.utils.evolution_client import EvolutionAPIClient

        client = EvolutionAPIClient()
        result = client.send_text(phone, message)
        logger.info("WhatsApp sent to %s", phone)
        return {"status": "sent", "phone": phone, "result": str(result)[:200]}
    except Exception as exc:
        logger.error("WhatsApp to %s failed: %s", phone, exc)
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "phone": phone, "error": str(exc)[:200]}


@shared_task
def dispatch_whatsapp_notifications(
    receiver_ids: list[str],
    actor_id: str,
    issue_id: str,
    project_identifier: str,
    project_name: str,
    issue_name: str,
    issue_sequence_id: int,
    activities: list[dict],
    sender_type: str = "",
    mention_ids: list[str] | None = None,
    comment_mention_ids: list[str] | None = None,
):
    """
    Dispatch WhatsApp notifications to all receivers that have a mobile_number.
    Called from the notifications task after in-app notifications are created.
    """
    if not getattr(settings, "EVOLUTION_API_URL", ""):
        return

    mention_ids = mention_ids or []
    comment_mention_ids = comment_mention_ids or []

    actor = User.objects.filter(pk=actor_id).first()
    actor_name = actor.display_name if actor else "Alguien"

    issue_identifier = f"{project_identifier}-{issue_sequence_id}"

    all_user_ids = set(receiver_ids) | set(mention_ids) | set(comment_mention_ids)
    all_user_ids.discard(actor_id)

    if not all_user_ids:
        return

    users = User.objects.filter(
        pk__in=all_user_ids,
        mobile_number__isnull=False,
    ).exclude(mobile_number="")

    user_map = {str(u.pk): u for u in users}

    notified_phones: set[str] = set()

    for uid in receiver_ids:
        if uid == actor_id:
            continue
        user = user_map.get(uid)
        if not user or user.mobile_number in notified_phones:
            continue
        msg = _build_message(
            actor_name=actor_name,
            issue_identifier=issue_identifier,
            issue_name=issue_name,
            project_name=project_name,
            activities=activities,
            sender_type=sender_type,
        )
        if msg:
            send_whatsapp_notification.delay(user.mobile_number, msg)
            notified_phones.add(user.mobile_number)

    for uid in comment_mention_ids:
        if uid == actor_id:
            continue
        user = user_map.get(uid)
        if not user or user.mobile_number in notified_phones:
            continue
        msg = _build_mention_message(actor_name, issue_identifier, issue_name, is_comment_mention=True)
        send_whatsapp_notification.delay(user.mobile_number, msg)
        notified_phones.add(user.mobile_number)

    for uid in mention_ids:
        if uid == actor_id:
            continue
        user = user_map.get(uid)
        if not user or user.mobile_number in notified_phones:
            continue
        msg = _build_mention_message(actor_name, issue_identifier, issue_name, is_comment_mention=False)
        send_whatsapp_notification.delay(user.mobile_number, msg)
        notified_phones.add(user.mobile_number)

    logger.info(
        "WhatsApp dispatch: %d messages for issue %s",
        len(notified_phones),
        issue_identifier,
    )
