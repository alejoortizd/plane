import os

from django.utils.deprecation import MiddlewareMixin


class ConditionalXFrameOptionsMiddleware(MiddlewareMixin):
    """
    Allow embedding in iframes from trusted origins specified via
    FRAME_ANCESTORS env var (comma-separated). Falls back to DENY
    when the variable is not set, matching Django's default behaviour.
    """

    def process_response(self, request, response):
        ancestors = os.environ.get("FRAME_ANCESTORS", "").strip()
        if ancestors:
            response["Content-Security-Policy"] = (
                f"frame-ancestors 'self' {ancestors}"
            )
            if "X-Frame-Options" in response:
                del response["X-Frame-Options"]
        else:
            response["X-Frame-Options"] = "DENY"
        return response
