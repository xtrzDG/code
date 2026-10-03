"""Flitt clients over scripted transports and the SHA-1 signature helper."""

import hashlib

import httpx

from app.clients.flitt.flitt_client import FlittClient
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from tests.billing.billing_settings import FLITT_MERCHANT_ID, FLITT_SECRET_KEY
from tests.billing.flitt_sandbox import FlittSandbox


def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def build_client(handler: FlittSandbox | None = None) -> FlittClient:
    sandbox: FlittSandbox = handler or FlittSandbox()
    return FlittClient(
        merchant_id=PlatformIdentifier(FLITT_MERCHANT_ID),
        secret_key=PlatformSecret(FLITT_SECRET_KEY),
        transport=httpx.MockTransport(sandbox.handle),
    )


def build_client_with(handler: httpx.MockTransport) -> FlittClient:
    return FlittClient(
        merchant_id=PlatformIdentifier(FLITT_MERCHANT_ID),
        secret_key=PlatformSecret(FLITT_SECRET_KEY),
        api_base_url=PublicBaseUrl("https://pay.flitt.example"),
        transport=handler,
    )
