"""
Webhook payloads shaped like the platforms' documented samples (WhatsApp
Cloud API, Telegram Bot API, Messenger and Instagram Messaging), one per
provider in `fixtures/`, with every kind of attachment a customer can send.
"""

import json
from pathlib import Path
from typing import Any

from app.schemas.dto.channels.channel_webhooks import ChannelWebhookPayload

FIXTURES_DIRECTORY: Path = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES_DIRECTORY / name).read_text(encoding="utf-8"))


def as_payload(body: Any) -> ChannelWebhookPayload:
    return ChannelWebhookPayload(body=json.dumps(body).encode("utf-8"))
