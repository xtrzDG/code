"""
End to end over HTTP: a Telegram customer books, sends STOP, the owner
erases their data, and the same account books again. The suppression list
remembers the STOP through the erasure: the new visit gets no reminder and
no request for feedback, and START from the same account brings them back.
"""

from fastapi.testclient import TestClient

from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret
from tests.e2e.harness import Workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.journeys import (
    BOOKING_REQUEST_RU,
    BUSINESS_BOT_TOKEN,
    JsonObject,
    OpenRestaurant,
    open_restaurant,
)

CUSTOMER_CHAT: int = 9001
FEEDBACK_DELAY_MINUTES: int = 60


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


def customer_contacts(client: TestClient, restaurant: OpenRestaurant) -> list[str]:
    listed = client.get(f"{restaurant.base}/contacts", headers=restaurant.headers)
    assert listed.status_code == 200, listed.text
    return [
        str(item["id"])
        for item in listed.json()["items"]
        if "telegram" in item["channels"] and item.get("erased_at") is None
    ]


def test_a_stop_outlives_the_erasure_of_the_customer(workshop: Workshop) -> None:
    client = workshop.client
    restaurant = open_restaurant(workshop)
    customer = TelegramCustomer(workshop, restaurant)
    assert customer.writes(BOOKING_REQUEST_RU)[-1].endswith(
        "Ваш столик забронирован на 19:00."
    )

    stopped = customer.writes("СТОП")
    assert len(stopped) == 1
    assert stopped[0].startswith("Готово: Salobie Bia больше не будет")

    # The owner erases the customer on request (a fresh sign-in counts as
    # the step-up).
    [contact_id] = customer_contacts(client, restaurant)
    erased = client.delete(
        f"{restaurant.base}/contacts/{contact_id}", headers=restaurant.headers
    )
    assert erased.status_code == 204, erased.text
    assert customer_contacts(client, restaurant) == []

    # The same account comes back and books again: a new contact, which
    # remembers nothing of the STOP.
    assert customer.writes(BOOKING_REQUEST_RU)[-1].endswith(
        "Ваш столик забронирован на 19:00."
    )
    [new_contact_id] = customer_contacts(client, restaurant)
    assert new_contact_id != contact_id
    contact = client.get(
        f"{restaurant.base}/contacts/{new_contact_id}", headers=restaurant.headers
    ).json()["contact"]
    assert contact["opted_out_channels"] == []

    settings = client.put(
        f"{restaurant.base}/review-settings",
        json={"is_feedback_enabled": True, "delay_minutes": FEEDBACK_DELAY_MINUTES},
        headers=restaurant.headers,
    )
    assert settings.status_code == 200, settings.text

    # The visit happens and ends; the worker's reminders and requests for
    # feedback come due, and none reaches the customer.
    sent_before_the_visit = len(customer.received())
    worker = workshop.container.gateways.background_worker()
    for _ in range(4 * 9):  # 36 hours in steps of an hour
        workshop.clock.advance(60 * 60)
        assert worker.run_once().failures == 0
    assert len(customer.received()) == sent_before_the_visit

    requests: list[JsonObject] = client.get(
        f"{restaurant.base}/feedback-requests", headers=restaurant.headers
    ).json()["items"]
    mine = [item for item in requests if item["contact_id"] == new_contact_id]
    assert [(item["status"], item["skip_reason"]) for item in mine] == [
        ("skipped", "opted_out")
    ]
    assert all(item["status"] != "sent" for item in requests)

    # START from the same account lifts the list's entry.
    welcomed = customer.writes("СТАРТ")
    assert len(welcomed) == 1
    # (after a day and a half, the assistant introduces itself again)
    assert "С возвращением! Salobie Bia снова будет" in welcomed[0]
