"""End to end over HTTP through the channels: a Telegram customer's booking
and its reminder, and a staff reply from the cabinet in the website widget.
"""

from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret
from tests.e2e.harness import Workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.journeys import (
    BOOKING_REQUEST_RU,
    BUSINESS_BOT_TOKEN,
    WIDGET_SESSION,
    JsonObject,
    open_restaurant,
)


def test_telegram_customer_books_and_the_worker_sends_the_reminder(
    workshop: Workshop,
) -> None:
    client = workshop.client
    restaurant = open_restaurant(workshop)

    # The owner connects the business's own Telegram bot.
    connected = client.put(
        f"{restaurant.base}/channels/telegram",
        json={"bot_token": BUSINESS_BOT_TOKEN},
        headers=restaurant.headers,
    )
    assert connected.status_code == 200, connected.text
    assert connected.json()["account_id"] == "workshop_bot"
    assert connected.json()["has_credential"] is True
    channel_id = str(connected.json()["id"])
    secret = derive_telegram_webhook_secret(
        PlatformSecret(E2E_ENVIRONMENT["ENCRYPTION_KEY"]),
        ChannelSecret(BUSINESS_BOT_TOKEN),
    )

    # A customer writes to the bot; the answer goes back through Telegram.
    update = {
        "update_id": 1,
        "message": {
            "message_id": 11,
            "date": 1791187200,
            "from": {"id": 9001, "is_bot": False, "first_name": "Nino"},
            "chat": {"id": 9001, "type": "private"},
            "text": BOOKING_REQUEST_RU,
        },
    }
    unsigned = client.post(f"/v1/channels/telegram/{channel_id}/webhook", json=update)
    delivered = client.post(
        f"/v1/channels/telegram/{channel_id}/webhook",
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": str(secret)},
    )
    repeated = client.post(
        f"/v1/channels/telegram/{channel_id}/webhook",
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": str(secret)},
    )
    assert unsigned.status_code == 401
    assert delivered.status_code == 200, delivered.text
    assert repeated.status_code == 200
    customer_replies = [
        body
        for body in workshop.telegram.bodies("sendMessage")
        if body["chat_id"] == "9001"
    ]
    assert len(customer_replies) == 1  # the redelivered update is not answered
    assert customer_replies[0]["text"].endswith("Ваш столик забронирован на 19:00.")
    bookings = client.get(
        f"{restaurant.base}/bookings", headers=restaurant.headers
    ).json()["items"]
    assert [booking["source_channel"] for booking in bookings] == ["telegram"]

    # The worker reminds the customer within a day of the booking, once.
    worker = workshop.container.gateways.background_worker()

    def reminders() -> list[JsonObject]:
        return [
            body
            for body in workshop.telegram.bodies("sendMessage")
            if body["chat_id"] == "9001" and body["text"].startswith("Напоминание")
        ]

    too_early = worker.run_once()  # tomorrow 19:00 Tbilisi is 31 hours away
    workshop.clock.advance(8 * 60 * 60)
    due = worker.run_once()
    workshop.clock.advance(15 * 60)
    again = worker.run_once()

    # Only the trace flush: the other jobs already ran in this period, when
    # the worker played the autotests (a new worker never repeats them).
    assert too_early.periodic_runs == 1
    assert [too_early.failures, due.failures, again.failures] == [0, 0, 0]
    assert len(reminders()) == 1
    reminder_text = str(reminders()[0]["text"])
    assert "«Salobie Bia»" in reminder_text
    assert "19:00" in reminder_text
    assert "Бесплатная отмена за 2 часа." in reminder_text


def test_staff_reply_from_the_cabinet_reaches_the_website_widget(
    workshop: Workshop,
) -> None:
    client = workshop.client
    restaurant = open_restaurant(workshop)
    web_chat = client.put(
        f"{restaurant.base}/channels/web", json={}, headers=restaurant.headers
    )
    assert web_chat.json()["status"] == "connected"
    widget_messages = f"/v1/widget/{restaurant.business_id}/messages"

    # A website visitor asks for a person; the assistant hands off.
    handed_off: JsonObject = client.post(
        widget_messages,
        json={"session_key": WIDGET_SESSION, "text": "Позовите, пожалуйста, менеджера"},
    ).json()
    assert handed_off["is_handed_off"] is True
    # The harness clock stands still, so the visitor's message and the answer
    # share a time; poll after the answer itself.
    caught_up = client.get(
        widget_messages,
        params={"after": handed_off["message_id"]},
        headers={"X-Widget-Session-Key": WIDGET_SESSION},
    ).json()
    assert caught_up["items"] == []
    assert caught_up["is_handed_off"] is True

    # The owner answers from the conversation card: the message is kept for
    # the widget, nothing goes through Telegram and the model is not asked.
    conversation_id = handed_off["conversation_id"]
    card = client.get(
        f"{restaurant.base}/conversations/{conversation_id}",
        headers=restaurant.headers,
    ).json()
    assert card["reply"] == {
        "is_available": True,
        "block": None,
        "delivery": "stored_for_widget",
        "window_closes_at": None,
        "template": None,
    }
    model_calls_before = workshop.model.assistant_calls
    telegram_sends_before = len(workshop.telegram.bodies("sendMessage"))
    workshop.clock.advance(60)  # the widget orders messages by their time
    sent = client.post(
        f"{restaurant.base}/conversations/{conversation_id}/messages",
        json={"text": "Здравствуйте, это Гиорги. Чем могу помочь?"},
        headers=restaurant.headers,
    )
    assert sent.status_code == 201, sent.text
    assert sent.json()["delivery"] == "stored_for_widget"
    staff_message: JsonObject = sent.json()["message"]
    assert staff_message["author"] == "staff"
    assert staff_message["direction"] == "outbound"
    assert staff_message["sent_by"] == restaurant.owner_id
    assert workshop.model.assistant_calls == model_calls_before
    assert len(workshop.telegram.bodies("sendMessage")) == telegram_sends_before

    # The widget's next poll brings the staff reply, once.
    polled = client.get(
        widget_messages,
        params={"after": caught_up["cursor"]},
        headers={
            "X-Widget-Session-Key": WIDGET_SESSION,
            "Origin": "https://salobie.example",
        },
    )
    assert polled.status_code == 200, polled.text
    assert polled.headers["access-control-allow-origin"] == "*"
    body: JsonObject = polled.json()
    assert body["items"] == [
        {
            "id": staff_message["id"],
            "author": "staff",
            "text": "Здравствуйте, это Гиорги. Чем могу помочь?",
            "language": "ru",
            "direction": "ltr",
            "created_at": staff_message["created_at"],
        }
    ]
    assert body["cursor"] == staff_message["id"]
    assert body["is_handed_off"] is True
    again = client.get(
        widget_messages,
        params={"after": body["cursor"]},
        headers={"X-Widget-Session-Key": WIDGET_SESSION},
    ).json()
    assert again["items"] == []
