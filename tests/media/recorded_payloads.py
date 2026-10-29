"""
Webhook bodies as the channels receive them. The payloads themselves are
contract fixtures shaped like the platforms' documented samples
(tests/contracts/meta/fixtures, tests/contracts/telegram/fixtures).
"""

import json
from typing import Any

from app.schemas.dto.channels.channel_webhooks import ChannelWebhookPayload


def as_payload(body: Any) -> ChannelWebhookPayload:
    return ChannelWebhookPayload(body=json.dumps(body).encode("utf-8"))
