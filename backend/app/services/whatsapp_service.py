import hashlib
import hmac
import logging
from typing import Optional

import httpx

from ..config import settings as s

logger = logging.getLogger(__name__)


class EvolutionClient:
    """
    Cliente HTTP para Evolution API v2.
    La API key nunca se expone en el frontend ni se loggea completa.
    """

    def __init__(self):
        self.base_url = self._sanitize_url(s.EVOLUTION_API_URL)
        self._api_key = s.EVOLUTION_API_KEY.strip() if s.EVOLUTION_API_KEY else ""

    @staticmethod
    def _sanitize_url(url: str) -> Optional[str]:
        url = url.strip().rstrip("/")
        if not url or "your-evolution" in url:
            return None
        return url

    def _key(self) -> Optional[str]:
        if not self._api_key or self._api_key == "change_me":
            return None
        return self._api_key

    def is_configured(self) -> bool:
        return self.base_url is not None and bool(self._key())

    def _require_config(self) -> tuple[str, str]:
        url = self.base_url
        key = self._key()
        if not url or not key:
            raise ValueError(
                "El servidor de WhatsApp (Evolution) no está configurado. "
                "Define EVOLUTION_API_URL y EVOLUTION_API_KEY en el .env."
            )
        return url, key

    @staticmethod
    def _extract_qr(data: Optional[dict]) -> Optional[str]:
        if not data:
            return None
        candidates = [
            data.get("base64"),
            (data.get("qrcode") or {}).get("base64") if isinstance(data.get("qrcode"), dict) else data.get("qrcode"),
            (data.get("qr") or {}).get("base64") if isinstance(data.get("qr"), dict) else data.get("qr"),
        ]
        for c in candidates:
            if isinstance(c, str) and c.strip():
                val = c.strip()
                if val.startswith("data:image"):
                    val = val.split(",")[-1] if "," in val else val
                return val
        return None

    @staticmethod
    def _extract_state(data: Optional[dict]) -> Optional[str]:
        if not data:
            return None
        instance = data.get("instance") or {}
        candidates = [
            instance.get("state") if isinstance(instance, dict) else None,
            instance.get("status") if isinstance(instance, dict) else None,
            data.get("state"),
            data.get("status"),
        ]
        for c in candidates:
            if isinstance(c, str) and c.strip():
                return c.strip().lower()
        return None

    async def _request(
        self, method: str, path: str, body: Optional[dict] = None, timeout: float = 25.0
    ) -> dict:
        url, key = self._require_config()
        full_url = f"{url}{path}"
        headers = {
            "apikey": key,
            "User-Agent": "spa-management-backend/1.0",
        }
        if body:
            headers["Content-Type"] = "application/json"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(method, full_url, headers=headers, json=body)
                text = response.text
                status = response.status_code
        except httpx.TimeoutException:
            logger.error(f"Evolution timeout en {method} {path}")
            raise ValueError("El servidor de WhatsApp (Evolution) no respondió a tiempo.")
        except httpx.HTTPError as exc:
            logger.error(f"Evolution error de red en {method} {path}: {exc}")
            raise ValueError("No se pudo contactar el servidor de WhatsApp.")

        if status >= 400:
            logger.error(f"Evolution {method} {path} -> {status}: {text[:200]}")
            raise ValueError(f"Evolution respondió {status} en {path}.")

        logger.debug(f"Evolution {method} {path} OK (len={len(text)})")

        try:
            return response.json() if text else {}
        except Exception as exc:
            logger.error(f"Evolution respuesta no JSON: {exc}")
            return {}

    async def connection_state(self, instance_name: str) -> Optional[str]:
        try:
            data = await self._request("GET", f"/instance/connectionState/{instance_name}")
            return self._extract_state(data)
        except ValueError as e:
            if "404" in str(e) or "respondió 404" in str(e):
                return None
            logger.warning(f"connection_state error: {e}")
            return None

    async def create_instance(self, instance_name: str) -> dict:
        data = await self._request("POST", "/instance/create", {
            "instanceName": instance_name,
            "token": self._key(),
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        })
        qr = self._extract_qr(data)
        state = self._extract_state(data)
        logger.info(f"create_instance {instance_name}: state={state}, qr_len={len(qr) if qr else 0}")
        return {
            "instance_name": instance_name,
            "state": state,
            "qr": qr,
        }

    async def connect(self, instance_name: str) -> dict:
        data = await self._request("GET", f"/instance/connect/{instance_name}")
        qr = self._extract_qr(data)
        state = self._extract_state(data)
        logger.info(f"connect {instance_name}: state={state}, qr_len={len(qr) if qr else 0}")
        return {
            "state": state,
            "qr": qr,
        }

    async def logout(self, instance_name: str):
        await self._request("DELETE", f"/instance/logout/{instance_name}")

    async def send_text(self, instance_name: str, number: str, text: str):
        await self._request("POST", f"/message/sendText/{instance_name}", {
            "number": number,
            "text": text,
        })

    async def set_webhook(self, instance_name: str, url: str):
        await self._request("POST", f"/webhook/set/{instance_name}", {
            "webhook": {
                "enabled": True,
                "url": url,
                "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"],
            },
        })


# Singleton compartido
evolution_client = EvolutionClient()