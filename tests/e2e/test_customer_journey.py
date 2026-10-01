"""
The product end to end over HTTP: the real container, scripted model, fake
external services (see harness.py).
"""

from collections.abc import Iterator

import pytest

from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret
from tests.e2e.harness import (
    ADMIN_EMAIL,
    API_BASE_URL,
    E2E_ENVIRONMENT,
    PLATFORM_BOT_TOKEN,
    Workshop,
    bearer,
    start_workshop,
)
from tests.e2e.journeys import (
    BOOKING_REQUEST_RU,
    BUSINESS_BOT_TOKEN,
    GEORGIAN_OWNER_PHONE,
    WIDGET_SESSION,
    WIZARD_STEPS,
    JsonObject,
    open_restaurant,
    sign_in_and_create_restaurant,
)


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    workshop = start_workshop()
    with workshop.client:
        yield workshop


def test_georgian_restaurant_from_sign_in_to_a_booked_and_handed_off_chat(
    workshop: Workshop,
) -> None:
    client = workshop.client
    # The platform bot is pointed at this API at startup.
    assert workshop.telegram.paths() == [
        f"/bot{PLATFORM_BOT_TOKEN}/getMe",
        f"/bot{PLATFORM_BOT_TOKEN}/setWebhook",
    ]
    assert workshop.telegram.bodies("setWebhook")[0]["url"] == (
        f"{API_BASE_URL}/v1/channels/telegram-platform/webhook"
    )

    # Sign in with a Georgian mobile number typed with spaces.
    token, session = workshop.sign_in_with_phone(GEORGIAN_OWNER_PHONE)
    headers = bearer(token)
    assert session["is_new_user"] is True
    assert session["user"]["phone_number"] == "+995555123456"
    assert session["user"]["country_code"] == "GE"
    assert workshop.otp.codes[-1].channel is OtpDeliveryChannel.SMS

    # A business in Georgia gets the country's defaults.
    created = client.post(
        "/v1/businesses",
        json={"name": "Salobie Bia", "niche_key": "restaurant"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    business: JsonObject = created.json()
    assert (business["country_code"], business["currency_code"]) == ("GE", "GEL")
    assert business["timezone"] == "Asia/Tbilisi"
    assert business["languages"] == ["ka", "ru", "en"]
    assert business["status"] == "onboarding"
    base = f"/v1/businesses/{business['id']}"

    # Profile wizard: six steps, then nothing blocks the assembly.
    wizard = client.get(f"{base}/profile/wizard", headers=headers)
    assert [step["step"] for step in wizard.json()["steps"]] == list(WIZARD_STEPS)
    for step, body in WIZARD_STEPS.items():
        saved = client.put(f"{base}/profile/steps/{step}", json=body, headers=headers)
        assert saved.status_code == 200, (step, saved.text)

    # Knowledge with prices in lari, a table, a holiday.
    faq = client.post(
        f"{base}/knowledge",
        json={"kind": "faq", "title": "Можно с собакой?", "body": "Да, на веранде."},
        headers=headers,
    )
    assert faq.status_code == 201, faq.text
    knowledge = client.get(f"{base}/knowledge", headers=headers).json()["items"]
    prices = {item["title"]: item["formatted_price"] for item in knowledge}
    assert prices["ხაჭაპური"] == "18,00\xa0₾"
    assert prices["Хинкали"] == "1,50\xa0₾"
    assert {item["currency_code"] for item in knowledge if item["price_minor"]} == {
        "GEL"
    }
    table = client.post(
        f"{base}/resources",
        json={"name": "Стол у окна", "capacity": 4, "unit_count": 3},
        headers=headers,
    )
    assert table.status_code == 201, table.text
    holiday = client.post(
        f"{base}/schedule-exceptions",
        json={"date": "2026-12-31", "note": "Новый год"},
        headers=headers,
    )
    assert holiday.status_code == 201, holiday.text
    # Staff get notifications in the platform Telegram bot; the widget is on.
    settings = client.patch(
        base,
        json={
            "manager_contacts": [
                {
                    "name": "Гиорги",
                    "channel": "telegram",
                    "address": "70001",
                    "language": "ru",
                }
            ]
        },
        headers=headers,
    )
    assert settings.status_code == 200, settings.text
    # Nothing blocking is left: the manager contact gets handoffs, bookings
    # and leads (the profile's handoff phone alone would reach nobody).
    gaps = client.get(
        f"{base}/profile/gaps", params={"language": "en"}, headers=headers
    )
    assert gaps.json()["is_ready_for_assembly"] is True
    web_chat = client.put(f"{base}/channels/web", json={}, headers=headers)
    assert web_chat.json()["status"] == "connected"
    dpa = client.post(f"{base}/dpa", json={}, headers=headers)
    assert dpa.json()["is_current_version_accepted"] is True
    trial = client.post(f"{base}/billing/trial", json={}, headers=headers)
    assert trial.status_code == 201, trial.text
    assert trial.json()["subscription"]["status"] == "trialing"

    # Assemble a version: every tool, the business languages, voice included.
    assembled = client.post(
        f"{base}/assistant-versions",
        json={"run_autotests": False},
        headers=headers,
    )
    assert assembled.status_code == 201, assembled.text
    version: JsonObject = assembled.json()
    version_id = str(version["id"])
    assert version["status"] == "draft"
    assert version["languages"] == ["ka", "ru", "en"]
    assert "create_booking" in version["tools"]
    assert version["is_voice_enabled"] is True
    assert "18.00 GEL" in str(version["facts"])

    # Autotests in Georgian: an AI customer asks prices, a judge scores.
    run = client.post(
        f"{base}/assistant-versions/{version_id}/autotests",
        json={"languages": ["ka"], "kinds": ["price_question"]},
        headers=headers,
    )
    assert run.status_code == 200, run.text
    report: JsonObject = run.json()
    assert report["version_status"] == "ready"
    assert report["is_passed"] is True
    assert report["scenario_count"] == report["passed_count"] == 3
    first_answer = report["results"][0]["transcript"][1]["text"]
    assert "18,00\xa0₾" in first_answer
    assert workshop.model.judge_calls == 3
    assert workshop.model.tool_calls == ["get_price"] * 3

    # Publishing sets up the ElevenLabs agent from the same version.
    published = client.post(
        f"{base}/assistant-versions/{version_id}/publish",
        json={},
        headers=headers,
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    assert published.json()["voice_agent_id"] == "agent_e2e"
    assert "/v1/convai/agents/create" in workshop.elevenlabs.paths()
    live = client.get(base, headers=headers).json()
    assert live["status"] == "live"
    assert live["published_assistant_version_id"] == version_id

    # A website visitor books a table through the tool loop.
    widget_origin = {"Origin": "https://salobie.example"}
    booked = client.post(
        f"/v1/widget/{business['id']}/messages",
        json={
            "session_key": WIDGET_SESSION,
            "text": BOOKING_REQUEST_RU,
            "contact_name": "Нино",
        },
        headers=widget_origin,
    )
    assert booked.status_code == 200, booked.text
    assert booked.headers["access-control-allow-origin"] == "*"
    reply: JsonObject = booked.json()
    assert reply["language"] == "ru"
    assert reply["is_handed_off"] is False
    assert reply["text"].startswith("Здравствуйте! Я AI-ассистент «Salobie Bia».")
    assert reply["text"].endswith("Ваш столик забронирован на 19:00.")
    assert workshop.model.tool_calls[-2:] == ["check_availability", "create_booking"]
    bookings = client.get(f"{base}/bookings", headers=headers).json()["items"]
    assert len(bookings) == 1
    assert bookings[0]["date"] == "2026-10-06"
    assert bookings[0]["time"] == "19:00"
    assert bookings[0]["contact_phone_number"] == "+995555123456"
    assert bookings[0]["source_channel"] == "web_chat"
    assert bookings[0]["status"] == "confirmed"
    staff_messages = workshop.telegram.bodies("sendMessage")
    assert staff_messages[-1]["chat_id"] == "70001"
    assert staff_messages[-1]["text"].startswith("Новая бронь · Salobie Bia")

    # The visitor asks for a person: staff are notified, the bot goes silent.
    handed_off = client.post(
        f"/v1/widget/{business['id']}/messages",
        json={"session_key": WIDGET_SESSION, "text": "Позовите, пожалуйста, менеджера"},
    ).json()
    assert handed_off["is_handed_off"] is True
    assert handed_off["text"] == "Ваш вопрос передан коллеге. Вам скоро ответят."
    assert (
        "Клиенту нужен человек" in workshop.telegram.bodies("sendMessage")[-1]["text"]
    )
    model_calls_before = workshop.model.assistant_calls
    silent = client.post(
        f"/v1/widget/{business['id']}/messages",
        json={"session_key": WIDGET_SESSION, "text": "Алло?"},
    ).json()
    assert silent["text"] is None
    assert silent["is_handed_off"] is True
    assert workshop.model.assistant_calls == model_calls_before

    # Cabinet: the conversation, the handoff and the dashboard.
    conversations = client.get(f"{base}/conversations", headers=headers).json()
    assert [item["status"] for item in conversations] == ["handoff"]
    handoffs = client.get(f"{base}/handoffs", headers=headers).json()["items"]
    assert [item["reason"] for item in handoffs] == ["customer_request"]
    dashboard = client.get(f"{base}/dashboard", headers=headers).json()
    assert dashboard["timezone"] == "Asia/Tbilisi"
    assert dashboard["conversation_count"] == 1
    assert dashboard["customer_message_count"] == 3
    assert dashboard["booking_count"] == 1
    assert dashboard["handoff_count"] == 1
    assert dashboard["languages"] == [{"language": "ru", "count": 1}]
    assert dashboard["channels"] == [{"channel": "web_chat", "count": 1}]


def test_second_owner_in_italy_is_isolated_and_admin_access_is_audited(
    workshop: Workshop,
) -> None:
    client = workshop.client
    georgian_token, _, georgian_business_id = sign_in_and_create_restaurant(workshop)
    georgian_base = f"/v1/businesses/{georgian_business_id}"

    # An owner signing in by e-mail opens a business in Italy.
    italian_token, italian_session = workshop.sign_in_with_email(
        "Giulia@Trattoria.example"
    )
    assert italian_session["user"]["email"] == "giulia@trattoria.example"
    assert workshop.otp.codes[-1].channel is OtpDeliveryChannel.EMAIL
    italian_headers = bearer(italian_token)
    created = client.post(
        "/v1/businesses",
        json={
            "name": "Trattoria Giulia",
            "niche_key": "restaurant",
            "country_code": "IT",
        },
        headers=italian_headers,
    )
    assert created.status_code == 201, created.text
    italian: JsonObject = created.json()
    assert (italian["currency_code"], italian["timezone"]) == ("EUR", "Europe/Rome")
    assert italian["languages"][0] == "it"

    # Neither owner sees the other's business, by any id.
    assert client.get(georgian_base, headers=italian_headers).status_code == 404
    for section in ("bookings", "conversations", "knowledge", "profile", "billing"):
        response = client.get(f"{georgian_base}/{section}", headers=italian_headers)
        assert response.status_code == 404, section
    assert (
        client.get(
            f"/v1/businesses/{italian['id']}", headers=bearer(georgian_token)
        ).status_code
        == 404
    )
    listed = client.get("/v1/businesses", headers=italian_headers).json()
    assert [item["name"] for item in listed] == ["Trattoria Giulia"]
    assert client.get("/v1/admin/clients", headers=italian_headers).status_code == 403

    # The platform admin sees every client; entering a cabinet is audited.
    admin_token, admin_session = workshop.sign_in_with_email(ADMIN_EMAIL)
    admin_headers = bearer(admin_token)
    assert admin_session["user"]["is_platform_admin"] is True
    clients = client.get("/v1/admin/clients", headers=admin_headers).json()
    assert clients["client_count"] == 2
    opened = client.post(
        f"/v1/admin/clients/{georgian_business_id}/open",
        headers=admin_headers,
    )
    assert opened.status_code == 200, opened.text
    assert "bookings" in opened.json()["sections"]
    admin_view = client.get(f"{georgian_base}/bookings", headers=admin_headers)
    assert admin_view.status_code == 200

    audit = client.get(
        f"{georgian_base}/audit-log", headers=bearer(georgian_token)
    ).json()
    admin_entries = [
        entry
        for entry in audit
        if entry["actor_id"] == admin_session["user"]["id"]
        and entry["action"] == "admin_access"
    ]
    assert {entry["entity"] for entry in admin_entries} == {
        "business",
        "business_cabinet",
    }


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

    assert too_early.periodic_runs == 7
    assert [too_early.failures, due.failures, again.failures] == [0, 0, 0]
    assert len(reminders()) == 1
    reminder_text = str(reminders()[0]["text"])
    assert "«Salobie Bia»" in reminder_text
    assert "19:00" in reminder_text
    assert "Бесплатная отмена за 2 часа." in reminder_text
