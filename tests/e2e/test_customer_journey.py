"""The product end to end over HTTP: the real container, scripted model, fake
external services (see harness.py). A Georgian restaurant from sign-in to a
booked and handed-off chat.
"""

from app.schemas.constants.localization import OtpDeliveryChannel
from tests.e2e.harness import Workshop, bearer
from tests.e2e.harness_settings import API_BASE_URL, PLATFORM_BOT_TOKEN
from tests.e2e.journeys import (
    BOOKING_REQUEST_RU,
    GEORGIAN_OWNER_PHONE,
    WIDGET_SESSION,
    WIZARD_STEPS,
    JsonObject,
)
from tests.e2e.widget_turns import answer_of, ask_widget, post_widget_message


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

    # A narrowed run (Georgian prices only) passes but proves nothing about
    # the other languages and scenarios: the version stays a draft.
    narrowed = client.post(
        f"{base}/assistant-versions/{version_id}/autotests",
        json={"languages": ["ka"], "kinds": ["price_question"]},
        headers=headers,
    )
    assert narrowed.status_code == 202, narrowed.text
    assert narrowed.json()["status"] == "running"
    assert workshop.model.judge_calls == 0  # nothing ran inside the request
    worker = workshop.container.gateways.background_worker()
    assert worker.run_once().queued_runs == 1
    narrowed_report: JsonObject = client.get(
        f"{base}/assistant-versions/{version_id}/autotest-run", headers=headers
    ).json()
    assert narrowed_report["status"] == "finished"
    assert narrowed_report["is_passed"] is True
    assert narrowed_report["is_full_coverage"] is False
    assert narrowed_report["version_status"] == "draft"
    assert narrowed_report["scenario_count"] == 3
    refused = client.post(
        f"{base}/assistant-versions/{version_id}/publish", json={}, headers=headers
    )
    assert refused.status_code == 409, refused.text

    # The full run: an AI customer plays every scenario in ka, ru and en
    # (prices, bookings, a request for a person, ...), then writes Hebrew
    # and German, which the business did not list, and Georgian and Russian
    # in Latin letters; a judge scores.
    started = client.post(
        f"{base}/assistant-versions/{version_id}/autotests",
        json={},
        headers=headers,
    )
    assert started.status_code == 202, started.text
    assert worker.run_once().queued_runs == 1
    report: JsonObject = client.get(
        f"{base}/assistant-versions/{version_id}/autotest-run", headers=headers
    ).json()
    assert report["id"] == started.json()["id"]
    assert report["version_status"] == "ready"
    assert report["is_passed"] is True
    assert report["is_full_coverage"] is True
    # 33 scenarios in ka, ru and en, and the four attacks in English.
    assert report["scenario_count"] == report["passed_count"] == 37
    results: dict[str, JsonObject] = {
        str(result["scenario_key"]): result for result in report["results"]
    }
    assert "18,00\xa0₾" in results["price_question__ka"]["transcript"][1]["text"]
    assert results["booking__en"]["transcript"][1]["text"].endswith(
        "Your table is booked for 19:00."
    )
    assert results["human_request__ka"]["transcript"][1]["text"].endswith(
        "თქვენი მოთხოვნა კოლეგას გადაეცა. მალე გიპასუხებენ."
    )
    assert results["foreign_language__he"]["transcript"][1]["text"].startswith(
        "שלום! אני עוזר ה-AI של"
    )
    assert results["foreign_language__de"]["transcript"][1]["text"].startswith(
        "Hallo! Ich bin der KI-Assistent von"
    )
    assert results["transliterated__ka"]["transcript"][0]["text"] == (
        "gamarjoba, kitxva makvs"
    )
    assert results["transliterated__ka"]["transcript"][1]["text"].startswith(
        "გამარჯობა!"
    )
    # Every play of both runs is judged (pass^k plays the launch-critical
    # scenarios twice).
    assert workshop.model.judge_calls == sum(
        result["sample_count"] or 1
        for run in (narrowed_report, report)
        for result in run["results"]
    )
    assert sorted(set(workshop.model.tool_calls)) == [
        "check_availability",
        "create_booking",
        "get_price",
        "handoff_to_human",
    ]

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
    booked = post_widget_message(
        workshop,
        business["id"],
        WIDGET_SESSION,
        BOOKING_REQUEST_RU,
        contact_name="Нино",
        headers=widget_origin,
    )
    assert booked.status_code == 202, booked.text
    assert booked.headers["access-control-allow-origin"] == "*"
    # The worker answers; the staff notice waits in the outbox until then.
    assert workshop.telegram.bodies("sendMessage") == []
    reply: JsonObject = answer_of(workshop, booked)
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
    # Staff hear about it from the outbox, sent by the worker.
    staff_messages = workshop.telegram.bodies("sendMessage")
    assert staff_messages[-1]["chat_id"] == "70001"
    assert staff_messages[-1]["text"].startswith("Новая бронь · Salobie Bia")

    # The visitor asks for a person: staff are notified, the bot goes silent.
    handed_off = ask_widget(
        workshop, business["id"], WIDGET_SESSION, "Позовите, пожалуйста, менеджера"
    )
    assert handed_off["is_handed_off"] is True
    assert handed_off["text"] == "Ваш вопрос передан коллеге. Вам скоро ответят."
    assert (
        "Клиенту нужен человек" in workshop.telegram.bodies("sendMessage")[-1]["text"]
    )
    model_calls_before = workshop.model.assistant_calls
    silent = ask_widget(workshop, business["id"], WIDGET_SESSION, "Алло?")
    assert silent["text"] is None
    assert silent["is_handed_off"] is True
    assert workshop.model.assistant_calls == model_calls_before

    # Cabinet: the conversation, the handoff and the dashboard.
    conversations = client.get(f"{base}/conversations", headers=headers).json()["items"]
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
