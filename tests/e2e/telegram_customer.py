"""A Telegram customer of the end-to-end restaurant, writing to its bot."""

from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret
from tests.e2e.harness import Workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.journeys import BUSINESS_BOT_TOKEN, OpenRestaurant

CUSTOMER_CHAT: int = 9001


class TelegramCustomer:
    """One Telegram account writing to the business's bot."""

    def __init__(self, workshop: Workshop, restaurant: OpenRestaurant) -> None:
        self._workshop: Workshop = workshop
        connected = workshop.client.put(
            f"{restaurant.base}/channels/telegram",
            json={"bot_token": BUSINESS_BOT_TOKEN},
            headers=restaurant.headers,
        )
        assert connected.status_code == 200, connected.text
        self._webhook: str = f"/v1/channels/telegram/{connected.json()['id']}/webhook"
        self._secret: str = str(
            derive_telegram_webhook_secret(
                PlatformSecret(E2E_ENVIRONMENT["ENCRYPTION_KEY"]),
                ChannelSecret(BUSINESS_BOT_TOKEN),
            )
        )
        self._update_id: int = 0

    def writes(self, text: str) -> list[str]:
        """Send `text`, let the worker answer, return what the bot sent back."""

        before: int = len(self.received())
        self._update_id += 1
        delivered = self._workshop.client.post(
            self._webhook,
            json={
                "update_id": self._update_id,
                "message": {
                    "message_id": 100 + self._update_id,
                    "date": 1791187200,
                    "from": {"id": CUSTOMER_CHAT, "is_bot": False, "first_name": "N"},
                    "chat": {"id": CUSTOMER_CHAT, "type": "private"},
                    "text": text,
                },
            },
            headers={"X-Telegram-Bot-Api-Secret-Token": self._secret},
        )
        assert delivered.status_code == 200, delivered.text
        self._workshop.run_queued_jobs()
        return self.received()[before:]

    def received(self) -> list[str]:
        return [
            str(body["text"])
            for body in self._workshop.telegram.bodies("sendMessage")
            if body["chat_id"] == str(CUSTOMER_CHAT)
        ]
