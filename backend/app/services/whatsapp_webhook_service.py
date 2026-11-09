import hashlib
import hmac
import logging
from typing import Optional, Union

logger = logging.getLogger(__name__)


def is_record(value: object) -> bool:
    return isinstance(value, dict)


def timing_safe_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def token_matches(received: str, expected: str) -> bool:
    return timing_safe_compare(received, expected)


def extract_evolution_text(data: Optional[dict]) -> Optional[str]:
    if not data:
        return None
    message = data.get("message")
    if not isinstance(message, dict):
        return None

    candidates = [
        message.get("conversation"),
        message.get("extendedTextMessage", {}).get("text") if isinstance(message.get("extendedTextMessage"), dict) else None,
        message.get("imageMessage", {}).get("caption") if isinstance(message.get("imageMessage"), dict) else None,
        message.get("videoMessage", {}).get("caption") if isinstance(message.get("videoMessage"), dict) else None,
        message.get("buttonsResponseMessage", {}).get("selectedDisplayText") if isinstance(message.get("buttonsResponseMessage"), dict) else None,
        message.get("listResponseMessage", {}).get("title") if isinstance(message.get("listResponseMessage"), dict) else None,
    ]
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip()[:2000]
    return None


def parse_evolution_webhook(body: Union[dict, list, None]) -> dict:
    """
    Normaliza el payload del webhook de Evolution.
    Retorna un dict con kind: 'connection', 'message' o 'ignored'.
    """
    if not isinstance(body, dict):
        return {"kind": "ignored"}

    event = str(body.get("event", "")).lower()

    if event == "connection.update":
        data = body.get("data")
        state = None
        if isinstance(data, dict):
            state = str(data.get("state", "")).strip().lower() if isinstance(data.get("state"), str) else None
        if not state:
            return {"kind": "ignored"}
        return {"kind": "connection", "state": state}

    if event != "messages.upsert":
        return {"kind": "ignored"}

    data = body.get("data")
    if not isinstance(data, dict):
        return {"kind": "ignored"}

    key = data.get("key")
    if not isinstance(key, dict):
        return {"kind": "ignored"}

    remote_jid = key.get("remoteJid")
    if not isinstance(remote_jid, str):
        return {"kind": "ignored"}

    if "@g.us" in remote_jid or "@broadcast" in remote_jid or "status@broadcast" in remote_jid:
        return {"kind": "ignored"}

    phone = remote_jid.split("@")[0].replace("-", "").replace(" ", "")
    if not phone.isdigit():
        return {"kind": "ignored"}

    return {
        "kind": "message",
        "phone": phone,
        "fromMe": key.get("fromMe") is True,
        "messageId": key.get("id") if isinstance(key.get("id"), str) else None,
        "pushName": data.get("pushName") if isinstance(data.get("pushName"), str) else None,
        "text": extract_evolution_text(data),
    }