"""
A Google calendar linked to a table: its free/busy answer takes the table's
slots, the account's calendars are listed to choose from, failures are
explained, the mirror calendar does not count the business's own bookings,
and unlinking frees the slots.
"""

from tests.calendar_sync.calendar_shop import open_calendar_shop
from tests.calendar_sync.fake_google_calendars import PRIMARY_CALENDAR, TEAM_CALENDAR

TEAM_MEETING: tuple[str, str] = ("2026-10-06T10:00:00Z", "2026-10-06T11:00:00Z")


def test_the_calendar_list_needs_a_connection_then_lists_primary_first() -> None:
    with open_calendar_shop() as shop:
        path = f"{shop.base}/integrations/google-calendar/calendars"
        before = shop.get(path)
        shop.connect_google()
        after = shop.get(path)

    assert before.status_code == 200, before.text
    assert before.json() == {
        "is_readable": False,
        "problem": "not_connected",
        "items": [],
    }
    assert after.json()["is_readable"] is True
    assert [item["calendar_id"] for item in after.json()["items"]] == [
        PRIMARY_CALENDAR,
        TEAM_CALENDAR,
    ]
    assert after.json()["items"][0]["is_primary"] is True


def test_a_linked_calendar_takes_the_slots_it_is_busy_in() -> None:
    with open_calendar_shop() as shop:
        shop.connect_google()
        shop.google.busy[TEAM_CALENDAR] = [TEAM_MEETING]
        linked = shop.put(f"{shop.calendar}/google", {"calendar_id": TEAM_CALENDAR})
        free = shop.free_times()
        query = shop.google.free_busy_queries[-1]

    assert linked.status_code == 200, linked.text
    google = linked.json()["google"]
    assert google["calendar_id"] == TEAM_CALENDAR
    assert google["status"]["block_count"] == 1
    assert free == ["12:00", "12:30", "13:00", "15:00", "15:30", "16:00"]
    assert query["items"] == [{"id": TEAM_CALENDAR}]


def test_unlinking_the_calendar_frees_its_slots() -> None:
    with open_calendar_shop() as shop:
        shop.connect_google()
        shop.google.busy[TEAM_CALENDAR] = [TEAM_MEETING]
        shop.put(f"{shop.calendar}/google", {"calendar_id": TEAM_CALENDAR})
        unlinked = shop.delete(f"{shop.calendar}/google")
        free = shop.free_times()
        view = shop.view()

    assert unlinked.status_code == 204, unlinked.text
    assert "14:00" in free
    assert view["google"]["calendar_id"] is None
    assert view["upcoming_busy_times"] == []


def test_a_lost_permission_asks_to_reconnect_and_keeps_nothing_new() -> None:
    with open_calendar_shop() as shop:
        shop.connect_google()
        shop.google.free_busy_status = 403
        linked = shop.put(f"{shop.calendar}/google", {"calendar_id": TEAM_CALENDAR})

    status = linked.json()["google"]["status"]
    assert status["problem"] == "needs_reconnect"
    assert status["block_count"] == 0


def test_an_unknown_calendar_is_reported_as_not_found() -> None:
    with open_calendar_shop() as shop:
        shop.connect_google()
        linked = shop.put(
            f"{shop.calendar}/google", {"calendar_id": "gone@group.calendar.google.com"}
        )
        empty = shop.put(f"{shop.calendar}/google", {"calendar_id": "  "})

    assert linked.json()["google"]["status"]["problem"] == "not_found"
    assert empty.status_code == 422, empty.text
    assert empty.json()["reasons"][0]["code"] == "calendar_invalid"


def test_a_calendar_linked_without_a_connection_says_so() -> None:
    with open_calendar_shop() as shop:
        linked = shop.put(f"{shop.calendar}/google", {"calendar_id": TEAM_CALENDAR})

    google = linked.json()["google"]
    assert google["is_connected"] is False
    assert google["status"]["problem"] == "not_connected"


def test_the_mirror_calendar_does_not_count_the_business_own_bookings() -> None:
    with open_calendar_shop() as shop:
        shop.connect_google()
        booked = shop.book("14:00")
        # Google reports the mirrored booking and one event of its own.
        shop.google.busy["primary"] = [
            ("2026-10-06T10:00:00Z", "2026-10-06T11:00:00Z"),
            ("2026-10-06T12:00:00Z", "2026-10-06T12:30:00Z"),
        ]
        linked = shop.put(f"{shop.calendar}/google", {"calendar_id": "primary"})

    assert booked.status_code == 201, booked.text
    busy = linked.json()["upcoming_busy_times"]
    assert [(item["source"], item["starts_at"]) for item in busy] == [
        ("google", 1_791_288_000)
    ]
