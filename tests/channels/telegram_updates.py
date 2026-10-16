"""Telegram updates for the channel tests and how to connect a bot and post them."""

from typing import Any

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.channel_endpoints import TELEGRAM_SECRET_HEADER
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret
from tests.channels.channels_payloads import HttpResponse, telegram_ok, to_json_bytes
from tests.channels.channels_settings import ENCRYPTION_KEY, TELEGRAM_BOT_TOKEN
from tests.channels.testbed import ChannelsTestbed

BOT_SECRET: str = str(
    derive_telegram_webhook_secret(
        PlatformSecret(ENCRYPTION_KEY), ChannelSecret(TELEGRAM_BOT_TOKEN)
    )
)


def build_update(
    text: str | None = "Do you have a table for 4 tonight?",
    chat_id: int = 555_000_111,
    chat_type: str = "private",
    message_id: int = 17,
    contact: dict[str, Any] | None = None,
    is_bot: bool = False,
    language_code: str = "ka",
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "message_id": message_id,
        "date": 1_790_856_000,
        "chat": {"id": chat_id, "type": chat_type},
        "from": {
            "id": chat_id,
            "is_bot": is_bot,
            "first_name": "ნინო",
            "last_name": "Beridze",
            "language_code": language_code,
        },
    }
    if text is not None:
        message["text"] = text
    if contact is not None:
        message["contact"] = contact
    return {"update_id": 1001, "message": message}


def connect_bot(testbed: ChannelsTestbed) -> tuple[BusinessDocument, ChannelDocument]:
    owner_id = testbed.add_user("owner")
    business = testbed.add_business(owner_id)
    channel = testbed.add_channel(
        business.id, ChannelKind.TELEGRAM, "funicular_vr_bot", TELEGRAM_BOT_TOKEN
    )
    testbed.telegram_transport.respond("POST", r"/sendMessage$", telegram_ok({}))
    return business, channel


def post_update(
    testbed: ChannelsTestbed,
    channel: ChannelDocument,
    update: dict[str, Any],
    secret: str | None = BOT_SECRET,
) -> HttpResponse:
    headers: dict[str, str] = {} if secret is None else {TELEGRAM_SECRET_HEADER: secret}
    return testbed.build_http_client().post(
        f"/v1/channels/telegram/{channel.id}/webhook",
        content=to_json_bytes(update),
        headers=headers,
    )
