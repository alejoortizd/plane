import os
import uuid

import jwt
from django.http import HttpResponseRedirect, JsonResponse
from django.views import View

from plane.authentication.utils.login import user_login
from plane.authentication.utils.redirection_path import get_redirection_path
from plane.authentication.utils.host import base_host
from plane.db.models import User, Profile, Workspace, WorkspaceMember


class SSOCallbackEndpoint(View):
    """
    Accepts a short-lived JWT signed by AnalySST (shared secret) and
    auto-logs the user into Plane, creating the account if it doesn't
    exist yet.

    Query params:
        token  – JWT with {email, first_name, last_name, exp, iat}
        next   – optional redirect path after login
    """

    def get(self, request):
        secret = os.environ.get("SSO_SHARED_SECRET", "")
        if not secret:
            return JsonResponse(
                {"error": "SSO not configured on this instance"}, status=503
            )

        raw_token = request.GET.get("token", "")
        if not raw_token:
            return JsonResponse({"error": "Missing token"}, status=400)

        try:
            payload = jwt.decode(raw_token, secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return JsonResponse({"error": "Token expired"}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({"error": "Invalid token"}, status=401)

        email = payload.get("email", "").strip().lower()
        first_name = payload.get("first_name", "")
        last_name = payload.get("last_name", "")

        if not email:
            return JsonResponse({"error": "Token missing email"}, status=400)

        user = User.objects.filter(email=email).first()

        if user is None:
            user = User.objects.create(
                email=email,
                username=uuid.uuid4().hex,
                first_name=first_name,
                last_name=last_name,
                display_name=f"{first_name} {last_name}".strip() or email,
                is_email_verified=True,
                is_password_autoset=True,
                is_active=True,
            )
            Profile.objects.get_or_create(
                user=user,
                defaults={"language": "es"},
            )

            default_ws = Workspace.objects.filter(
                slug=os.environ.get("DEFAULT_WORKSPACE_SLUG", "analysst")
            ).first()
            if default_ws:
                WorkspaceMember.objects.get_or_create(
                    workspace=default_ws,
                    member=user,
                    defaults={"role": 15},
                )

        user_login(request=request, user=user, is_app=True)

        next_path = request.GET.get("next") or get_redirection_path(user=user)
        base = base_host(request=request, is_app=True)
        url = f"{base}/{next_path}" if next_path else base
        return HttpResponseRedirect(url)
