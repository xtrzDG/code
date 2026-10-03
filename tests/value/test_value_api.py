"""The cabinet's value routes on the real application with the demo data."""

import re
from collections.abc import Iterator

import pytest

from tests.value.value_demo import DEMO_OWNER_EMAIL, ValueDemo, open_value_demo


@pytest.fixture(scope="module")
def demo() -> Iterator[ValueDemo]:
    with open_value_demo() as opened:
        yield opened


def test_the_owner_sees_the_value_of_last_week_with_money(demo: ValueDemo) -> None:
    answer = demo.get("/value?period=last_week")

    assert answer.status_code == 200, answer.text
    model = answer.json()
    assert (model["date_from"], model["date_to"]) == ("2026-09-28", "2026-10-04")
    assert model["currency_code"] == "GEL"
    assert model["value_basis"] == "bookings"
    assert model["current"]["conversation_count"] > 0
    assert model["current"]["assistant_booking_count"] > 0
    assert model["average_check_source"] in {"niche_default", "owner"}
    assert model["current"]["estimated_revenue_minor"] == (
        model["current"]["assistant_booking_count"] * model["average_check_minor"]
    )


def test_staff_see_counts_without_money(demo: ValueDemo) -> None:
    model = demo.get("/value?from=2026-09-06&to=2026-10-05", demo.staff).json()

    assert model["current"]["estimated_revenue_minor"] is None
    assert model["average_check_minor"] is None
    assert model["previous_date_to"] == "2026-09-05"


@pytest.mark.parametrize(
    "query",
    ["period=yesterday", "from=05.10.2026", "from=2026-10-05&to=2026-10-01"],
)
def test_a_bad_period_is_refused(demo: ValueDemo, query: str) -> None:
    assert demo.get(f"/value?{query}").status_code == 422


def test_the_owner_sets_and_clears_the_average_check(demo: ValueDemo) -> None:
    before = demo.get("/value/settings").json()
    saved = demo.put("/value/settings", {"average_check_minor": 9_000})
    used = demo.get("/value?period=last_week").json()
    cleared = demo.put("/value/settings", {"average_check_minor": None}).json()

    assert before["average_check_minor"] is None
    assert before["typical_check_minor"] == 12_000
    assert saved.status_code == 200, saved.text
    assert saved.json()["average_check_minor"] == 9_000
    assert used["average_check_source"] == "owner"
    assert used["average_check_minor"] == 9_000
    assert cleared["average_check_minor"] is None
    assert demo.put("/value/settings", {"average_check_minor": -1}).status_code == 422


def test_staff_may_not_change_the_average_check(demo: ValueDemo) -> None:
    answer = demo.put("/value/settings", {"average_check_minor": 1}, demo.staff)

    assert answer.status_code == 403


def test_the_owner_turns_summaries_on_and_off(demo: ValueDemo) -> None:
    defaults = demo.get("/digest-preferences").json()
    changed = demo.put(
        "/digest-preferences",
        {
            "is_daily_digest_on": True,
            "is_weekly_digest_on": False,
            "is_monthly_report_on": True,
        },
    ).json()
    read_back = demo.get("/digest-preferences").json()

    assert (
        defaults["is_daily_digest_on"],
        defaults["is_weekly_digest_on"],
        defaults["is_monthly_report_on"],
    ) == (False, True, True)
    assert defaults["email"] == DEMO_OWNER_EMAIL
    assert defaults["device_count"] == 0
    assert changed["is_weekly_digest_on"] is False
    assert read_back == changed
    demo.put("/digest-preferences", {})


def test_todays_queue_counts_the_bookings_of_today(demo: ValueDemo) -> None:
    queue = demo.get("/today-queue", demo.staff).json()

    assert queue["date"] == "2026-10-05"
    assert queue["booking_count"] >= queue["upcoming_booking_count"] >= 0
    assert queue["unconfirmed_booking_count"] <= queue["upcoming_booking_count"]


def test_reports_are_listed_and_read_by_owners(demo: ValueDemo) -> None:
    demo.workshop.container.gateways.background_worker().run_once()

    page = demo.get("/value-reports?limit=10").json()
    [report] = page["items"]
    detail = demo.get(f"/value-reports/{report['id']}")

    assert page["next_cursor"] is None
    assert report["kind"] == "monthly" and report["period_key"] == "2026-09"
    assert detail.status_code == 200 and detail.json() == report
    assert demo.get("/value-reports?kind=hourly").status_code == 422
    assert demo.get("/value-reports", demo.staff).status_code == 403
    missing = "value_report_00000000-0000-5000-8000-000000000000"
    assert demo.get(f"/value-reports/{missing}").status_code == 404
    assert demo.get("/value-reports/not-an-id").status_code == 404


def test_a_digest_link_opens_its_report(demo: ValueDemo) -> None:
    demo.workshop.container.gateways.background_worker().run_once()

    [report] = demo.get("/value-reports").json()["items"]
    texts = [
        str(message.text)
        for message in demo.report_messages()
        if str(message.business_id) == demo.business_id
        and message.staff_contact is not None
        and f"value_report:{report['id']}" in str(message.idempotency_key)
    ]
    match = re.search(r"/n/([A-Za-z0-9_-]+)", texts[0])
    assert match is not None
    opened = demo.get(f"/notification-links/{match.group(1)}").json()

    assert opened["target"] == "report"
    assert opened["value_report_id"] == report["id"]
