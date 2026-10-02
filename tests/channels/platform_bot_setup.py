"""An owner, staff and business connected to the platform Telegram bot."""

from typing import Any

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.channel_endpoints import TELEGRAM_SECRET_HEADER
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret
from tests.channels.channels_payloads import (
    HttpResponse,
    bearer,
    telegram_ok,
    to_json_bytes,
)
from tests.channels.channels_settings import ENCRYPTION_KEY, GEORGIA, PLATFORM_BOT_TOKEN
from tests.channels.testbed import ChannelsTestbed

PLATFORM_SECRET: str = str(
    derive_telegram_webhook_secret(
        PlatformSecret(ENCRYPTION_KEY), PlatformSecret(PLATFORM_BOT_TOKEN)
    )
)

STAFF_CHAT_ID: int = 31_337


class PlatformBotSetup:
    def __init__(self, settings: Any = None) -> None:
        self.testbed = ChannelsTestbed(settings)
        self.owner_id = self.testbed.add_user("owner")
        self.staff_id = self.testbed.add_user("staff")
        self.business: BusinessDocument = self.testbed.add_business(
            self.owner_id,
            country=GEORGIA,
            staff_ids=[self.staff_id],
            owner_language="ru",
        )
        self.client = self.testbed.build_http_client()
        self.testbed.telegram_transport.respond(
            "POST", r"/getMe$", telegram_ok({"username": "workshop_staff_bot"})
        )
        self.testbed.telegram_transport.respond(
            "POST", r"/sendMessage$", telegram_ok({})
        )

    def create_link(self, body: dict[str, Any], token: str = "owner") -> HttpResponse:
        return self.client.post(
            f"/v1/businesses/{self.business.id}/manager-contacts/telegram-link",
            json=body,
            headers=bearer(token),
        )

    def send_to_bot(
        self,
        text: str,
        secret: str | None = PLATFORM_SECRET,
        chat_type: str = "private",
        language_code: str = "en",
    ) -> HttpResponse:
        update = {
            "update_id": 1,
            "message": {
                "message_id": 5,
                "chat": {"id": STAFF_CHAT_ID, "type": chat_type},
                "from": {
                    "id": STAFF_CHAT_ID,
                    "is_bot": False,
                    "language_code": language_code,
                },
                "text": text,
            },
        }
        headers = {} if secret is None else {TELEGRAM_SECRET_HEADER: secret}
        return self.client.post(
            "/v1/channels/telegram-platform/webhook",
            content=to_json_bytes(update),
            headers=headers,
        )

    def replies(self) -> list[str]:
        return [
            str(request.json()["text"])
            for request in self.testbed.telegram_transport.requests_to("/sendMessage")
        ]

    def stored_business(self) -> BusinessDocument:
        business = self.testbed.business_repo.get(self.business.id)
        assert business is not None
        return business
