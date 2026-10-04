"""
The help center, the support contacts and each person's guidance on the
real application: articles are public, cached and fall back to English;
coach marks and the changelog belong to the signed-in person.
"""

from collections.abc import Iterator
from typing import Any

import pytest

from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT

type JsonObject = dict[str, Any]

OWNER_PHONE: str = "+995 555 12 34 56"
SUPPORT_ENVIRONMENT: dict[str, str] = {
    **E2E_ENVIRONMENT,
    "SUPPORT_WHATSAPP": "+995 322 00-00-00",
    "SUPPORT_TELEGRAM": "@workshop_support",
    "SUPPORT_EMAIL": "Help@Workshop.example",
}


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    running = start_workshop(SUPPORT_ENVIRONMENT)
    with running.client:
        yield running


def test_the_help_center_is_public_and_grouped_by_topic(workshop: Workshop) -> None:
    response = workshop.client.get("/v1/help/ru")

    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "public, max-age=300"
    view: JsonObject = response.json()
    assert view["language"] == "ru"
    assert view["available_languages"] == ["en", "ka", "ru"]
    assert [topic["topic"] for topic in view["topics"]] == [
        "getting_started",
        "channels",
        "daily_work",
        "account",
    ]
    assert view["topics"][0]["articles"][0]["slug"] == "getting-started"


def test_an_article_opens_in_the_language_asked_or_english(
    workshop: Workshop,
) -> None:
    georgian = workshop.client.get("/v1/help/ka/call-forwarding")
    german = workshop.client.get("/v1/help/de-AT/call-forwarding")

    assert georgian.status_code == 200, georgian.text
    assert georgian.json()["title"] == "ზარების გადამისამართება"
    assert "**61*" in georgian.json()["markdown"]
    assert german.json()["language"] == "en"
    assert german.json()["title"] == "Call forwarding"
    assert [card["slug"] for card in german.json()["related"]] == ["channels", "inbox"]


@pytest.mark.parametrize(
    "path",
    ["/v1/help/en/refunds", "/v1/help/en/Bad_Slug", "/v1/help/not-a-language!"],
)
def test_unknown_articles_and_languages_are_not_found(
    workshop: Workshop, path: str
) -> None:
    assert workshop.client.get(path).status_code == 404


def test_search_finds_word_forms_and_needs_words(workshop: Workshop) -> None:
    found = workshop.client.get("/v1/help/ru/search", params={"q": "переадресацию"})
    empty = workshop.client.get("/v1/help/ru/search", params={"q": "  "})
    missing = workshop.client.get("/v1/help/ru/search")

    assert found.status_code == 200, found.text
    assert found.json()["items"][0]["slug"] == "call-forwarding"
    assert empty.status_code == 422
    assert missing.status_code == 422


def test_support_contacts_come_from_the_settings(workshop: Workshop) -> None:
    response = workshop.client.get("/v1/support/contacts")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "whatsapp_number": "+995322000000",
        "whatsapp_url": "https://wa.me/995322000000",
        "telegram_username": "workshop_support",
        "telegram_url": "https://t.me/workshop_support",
        "email": "help@workshop.example",
        "email_url": "mailto:help@workshop.example",
    }


def test_coach_marks_and_the_changelog_belong_to_the_person(
    workshop: Workshop,
) -> None:
    token, _ = workshop.sign_in_with_phone(OWNER_PHONE)
    headers = bearer(token)

    first = workshop.client.get("/v1/me/help", headers=headers)
    marked = workshop.client.put("/v1/me/help/coach-marks/inbox", headers=headers)
    read = workshop.client.put(
        "/v1/me/help/changelog",
        json={"read_key": "2026-10-04-help-center"},
        headers=headers,
    )
    reset = workshop.client.delete("/v1/me/help/coach-marks", headers=headers)
    after = workshop.client.get("/v1/me/help", headers=headers)

    assert first.json() == {"seen_coach_marks": [], "changelog_read_key": None}
    assert marked.json()["seen_coach_marks"] == ["inbox"]
    assert read.json()["changelog_read_key"] == "2026-10-04-help-center"
    assert reset.status_code == 204
    assert after.json() == {
        "seen_coach_marks": [],
        "changelog_read_key": "2026-10-04-help-center",
    }


def test_guidance_needs_a_sign_in_and_valid_keys(workshop: Workshop) -> None:
    token, _ = workshop.sign_in_with_phone(OWNER_PHONE)

    anonymous = workshop.client.get("/v1/me/help")
    bad_key = workshop.client.put(
        "/v1/me/help/coach-marks/Not A Key", headers=bearer(token)
    )
    bad_entry = workshop.client.put(
        "/v1/me/help/changelog", json={"read_key": "yesterday"}, headers=bearer(token)
    )

    assert anonymous.status_code == 401
    assert bad_key.status_code == 404
    assert bad_entry.status_code == 422
