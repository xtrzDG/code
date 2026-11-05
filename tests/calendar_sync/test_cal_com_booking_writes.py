"""
The whole application with a fake Cal.com: a booking of a table that
follows a Cal.com event type is written there by a queued job (the booking
itself never waits for Cal.com), moved there when it is moved and cancelled
there when it is cancelled; a write Cal.com refuses shows on the table's
calendar card until a retry goes through.
"""

from typing import Any

from tests.calendar_sync.calendar_shop import CalendarShop, open_calendar_shop
from tests.calendar_sync.fake_cal_com import GOOD_KEY

type JsonObject = dict[str, Any]

# Past the queue's first retry delay.
RETRY_WAIT_SECONDS: int = 10 * 60


def follow_cal_com(shop: CalendarShop) -> None:
    linked = shop.put(
        f"{shop.calendar}/booking-system",
        {"kind": "cal_com", "external_resource_id": "1203845", "api_key": GOOD_KEY},
    )
    assert linked.status_code == 200, linked.text


def book(shop: CalendarShop, time: str) -> JsonObject:
    booked = shop.book(time)
    assert booked.status_code == 201, booked.text
    return dict(booked.json()["booking"])


def writes_of(shop: CalendarShop) -> JsonObject:
    return dict(shop.view()["booking_system"]["write_status"])


def test_a_booking_is_written_moved_and_cancelled_in_cal_com() -> None:
    with open_calendar_shop() as shop:
        follow_cal_com(shop)
        booking = book(shop, "13:00")
        before_the_job = list(shop.edges.cal_com.created)
        shop.workshop.run_queued_jobs()
        written = list(shop.edges.cal_com.created)
        moved = shop.post(
            f"{shop.base}/bookings/{booking['id']}/reschedule",
            {"new_date": "2026-10-06", "new_time": "15:00"},
        )
        shop.workshop.run_queued_jobs()
        after_the_move = shop.edges.cal_com.active_created()
        cancelled = shop.post(f"{shop.base}/bookings/{booking['id']}/cancel")
        shop.workshop.run_queued_jobs()
        status = writes_of(shop)

    assert before_the_job == []
    [first] = written
    assert first["start"] == "2026-10-06T09:00:00Z"
    assert first["metadata"] == {
        "source": "assistant-workshop",
        "booking_id": booking["id"],
    }
    assert first["attendee"]["name"] == "Nino"
    assert moved.status_code == 200, moved.text
    assert after_the_move == ["created-2"]
    assert shop.edges.cal_com.created[1]["start"] == "2026-10-06T11:00:00Z"
    assert cancelled.status_code == 200, cancelled.text
    assert shop.edges.cal_com.cancelled == ["created-1", "created-2"]
    assert shop.edges.cal_com.active_created() == []
    assert status["last_written_at"] is not None and status["problem"] is None


def test_the_platforms_own_booking_does_not_block_the_table_twice() -> None:
    with open_calendar_shop() as shop:
        follow_cal_com(shop)
        book(shop, "13:00")
        shop.workshop.run_queued_jobs()
        shop.post(f"{shop.calendar}/sync")
        free = shop.free_times()

    assert "13:00" not in free
    assert "14:00" in free
    assert len(shop.edges.cal_com.created) == 1


def test_a_refused_write_shows_on_the_card_until_a_retry_goes_through() -> None:
    with open_calendar_shop() as shop:
        follow_cal_com(shop)
        shop.edges.cal_com.refuses_writes = True
        book(shop, "13:00")
        shop.workshop.run_queued_jobs()
        failed = writes_of(shop)
        shop.edges.cal_com.refuses_writes = False
        shop.workshop.clock.advance(RETRY_WAIT_SECONDS)
        shop.workshop.run_queued_jobs()
        recovered = writes_of(shop)

    assert failed["problem"] == "provider_error"
    assert failed["last_failed_at"] is not None and failed["last_written_at"] is None
    assert failed["problem_detail"].startswith("Cal.com answered HTTP 400")
    assert recovered["problem"] is None
    assert recovered["last_written_at"] is not None
    assert shop.edges.cal_com.active_created() == ["created-1"]


def test_a_table_that_follows_no_booking_system_writes_nothing() -> None:
    with open_calendar_shop() as shop:
        book(shop, "13:00")
        shop.workshop.run_queued_jobs()

    assert shop.edges.cal_com.requests == []
