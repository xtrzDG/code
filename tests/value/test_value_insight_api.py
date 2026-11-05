"""Customer sources, topics and summary channels on the real app with the demo."""

from collections.abc import Iterator

import pytest

from tests.value.value_demo import ValueDemo, open_value_demo


@pytest.fixture(scope="module")
def demo() -> Iterator[ValueDemo]:
    with open_value_demo() as opened:
        yield opened


def test_the_owner_sees_where_customers_came_from(demo: ValueDemo) -> None:
    answer = demo.get("/value/sources?period=30d")

    assert answer.status_code == 200, answer.text
    view = answer.json()
    assert (view["date_from"], view["date_to"]) == ("2026-09-06", "2026-10-05")
    rows = {row["acquisition_source"] or row["kind"]: row for row in view["rows"]}
    assert rows["table"]["kind"] == "tagged"
    assert rows["table"]["conversation_count"] > 0
    assert "whatsapp" in rows["table"]["channels"]
    assert any(str(key).startswith("tel-") for key in rows)
    assert sum(row["conversation_count"] for row in view["rows"]) > 0
    assert sum(row["booking_count"] for row in view["rows"]) > 0


def test_sources_are_for_owners_and_known_periods(demo: ValueDemo) -> None:
    assert demo.get("/value/sources", demo.staff).status_code == 403
    assert demo.get("/value/sources?period=yesterday").status_code == 422


def test_owners_and_staff_read_what_customers_ask_about(demo: ValueDemo) -> None:
    view = demo.get("/value/topics", demo.staff).json()

    assert view["label_language"] == "ru"
    assert view["window_to"] is not None
    [largest, *_] = view["groups"]
    assert largest["conversation_count"] > 0
    assert largest["topics"][0]["conversation_count"] > 0
    labels = {topic["label"] for group in view["groups"] for topic in group["topics"]}
    assert "Бронирование" in labels


def test_the_inbox_shows_where_a_customer_came_from(demo: ValueDemo) -> None:
    page = demo.get("/inbox?view=all&limit=50").json()

    assert any(item.get("acquisition_source") for item in page["items"])


def test_summary_channels_that_cannot_reach_the_owner_are_refused(
    demo: ValueDemo,
) -> None:
    switches = {
        "is_daily_digest_on": False,
        "is_weekly_digest_on": True,
        "is_monthly_report_on": True,
    }
    unlinked = demo.put(
        "/digest-preferences",
        {**switches, "channels": ["telegram"], "telegram_chat": "999000999"},
    )
    no_template = demo.put(
        "/digest-preferences", {**switches, "channels": ["whatsapp"]}
    )
    email_only = demo.put("/digest-preferences", {**switches, "channels": ["email"]})
    read_back = demo.get("/digest-preferences").json()

    assert unlinked.status_code == 422
    assert unlinked.json()["reasons"][0]["code"] == "telegram_chat_not_linked"
    assert no_template.json()["reasons"][0]["code"] == "whatsapp_not_available"
    assert email_only.status_code == 200, email_only.text
    assert read_back["channels"] == ["email"]
    assert read_back["is_telegram_ready"] is True
    assert read_back["is_whatsapp_ready"] is False
    demo.put("/digest-preferences", {**switches, "channels": ["email", "push"]})
