"""Request helpers of the channels tests: signatures, JSON bodies and headers."""

import hashlib
import hmac
import json
from collections.abc import Mapping

import httpx2

from tests.channels.channels_settings import ELEVENLABS_WEBHOOK_SECRET, META_APP_SECRET

# Responses of FastAPI's TestClient (built on httpx2).
HttpResponse = httpx2.Response


def telegram_ok(result: object = True) -> dict[str, object]:
    return {"ok": True, "result": result}


def sign_meta(body: bytes, secret: str = META_APP_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def sign_elevenlabs(
    body: bytes,
    timestamp: int,
    secret: str = ELEVENLABS_WEBHOOK_SECRET,
) -> str:
    message: bytes = str(timestamp).encode() + b"." + body
    digest: str = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f"t={timestamp},v0={digest}"


def to_json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def headers_with(extra: Mapping[str, str]) -> dict[str, str]:
    return {"Content-Type": "application/json", **extra}
