import logging

import requests
from django.conf import settings

logger = logging.getLogger("plane.worker")


class EvolutionAPIClient:
    """Evolution API v2 client for WhatsApp messaging and instance management."""

    def __init__(self):
        self.api_url = settings.EVOLUTION_API_URL.rstrip("/")
        self.instance_name = settings.EVOLUTION_INSTANCE_NAME
        self.headers = {
            "apikey": settings.EVOLUTION_API_GLOBAL_KEY,
            "Content-Type": "application/json",
        }

    def _get(self, path: str) -> dict:
        url = f"{self.api_url}{path}"
        r = requests.get(url, headers=self.headers, timeout=15)
        r.raise_for_status()
        return r.json()

    def _delete(self, path: str) -> dict:
        url = f"{self.api_url}{path}"
        r = requests.delete(url, headers=self.headers, timeout=15)
        r.raise_for_status()
        return r.json()

    def get_connection_state(self) -> dict:
        return self._get(f"/instance/connectionState/{self.instance_name}")

    def connect_instance(self) -> dict:
        return self._get(f"/instance/connect/{self.instance_name}")

    def logout_instance(self) -> dict:
        return self._delete(f"/instance/logout/{self.instance_name}")

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
