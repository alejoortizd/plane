import logging

import requests
from django.conf import settings

logger = logging.getLogger("plane.worker")


class EvolutionAPIClient:
    """Minimal Evolution API v2 client for WhatsApp messaging."""

    def __init__(self):
        self.api_url = settings.EVOLUTION_API_URL.rstrip("/")
        self.instance_name = settings.EVOLUTION_INSTANCE_NAME
        self.headers = {
            "apikey": settings.EVOLUTION_API_GLOBAL_KEY,
            "Content-Type": "application/json",
        }

    def send_text(self, phone: str, text: str) -> dict:
        url = f"{self.api_url}/message/sendText/{self.instance_name}"
        try:
            r = requests.post(
                url,
                json={"number": phone, "text": text},
                headers=self.headers,
                timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            body = ""
            if hasattr(e, "response") and e.response is not None:
                try:
                    body = e.response.text[:500]
                except Exception:
                    pass
            logger.error(
                "Evolution API send_text to %s failed: %s | body: %s",
                phone,
                e,
                body,
            )
            raise
