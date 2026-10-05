"""
End to end over HTTP: what a guest may change through the manage link —
move the booking to a free time (a new link and a new confirmation follow),
cancel it, nothing once it started — and the limits of a public page.
"""

import threading

from app.schemas.dto.booking_manage import ManagedBookingRequest, ManagedBookingView
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.bookings.constrained_strings import (
    BookingManageToken,
    LocalDate,
    LocalTimeOfDay,
)
from tests.bookings.manage_journey import (
    BOOKINGS_PATH,
    book_a_table,
    manage_token,
    system_texts,
    widget_messages_after,
)
from tests.e2e.harness import Workshop
from tests.e2e.journeys import JsonObject

NEXT_DAY: str = "2026-10-07"
# From 2026-10-05 08:00 UTC to 15:30 UTC on the 6th: the visit has begun.
UNTIL_THE_VISIT_STARTED: int = (24 + 7) * 3600 + 30 * 60


def reasons(response: object) -> list[str]:
    body: JsonObject = response.json()  # type: ignore[attr-defined]
    return [str(reason["code"]) for reason in body["reasons"]]


def test_a_move_to_a_free_time_issues_a_new_link(workshop: Workshop) -> None:
    booked = book_a_table(workshop)

    slots = workshop.client.get(f"{booked.page}/slots", params={"date": NEXT_DAY})
    assert slots.status_code == 200, slots.text
    free: JsonObject = slots.json()
    assert (free["date"], free["booking_unit"], free["is_open_on_date"]) == (
        NEXT_DAY,
        "time_slot",
        True,
    )
    # Every free start of the day, not the assistant's first few.
    assert "20:00" in free["times"] and len(free["times"]) > 10

    workshop.clock.advance(60)  # the widget orders messages by their time
    moved = workshop.client.post(
        f"{booked.page}/reschedule", json={"date": NEXT_DAY, "time": "20:00"}
    )

    assert moved.status_code == 200, moved.text
    view: JsonObject = moved.json()
    assert (view["date"], view["time"], view["status"]) == (
        NEXT_DAY,
        "20:00",
        "confirmed",
    )
    assert view["token"] != booked.token
    stale = workshop.client.get(booked.page)
    assert stale.status_code == 404
    assert reasons(stale) == ["booking_changed"]
    assert workshop.client.get(f"{BOOKINGS_PATH}/{view['token']}").status_code == 200
    # The chat gets the new confirmation with the new link.
    polled = widget_messages_after(workshop, booked.restaurant, booked.cursor)
    [moved_text] = system_texts(polled)
    assert moved_text.startswith("Salobie Bia: ваша бронь перенесена.")
    assert manage_token(moved_text) == view["token"]


def test_a_time_outside_the_hours_is_refused(workshop: Workshop) -> None:
    booked = book_a_table(workshop)

    closed = workshop.client.post(
        f"{booked.page}/reschedule", json={"date": NEXT_DAY, "time": "03:00"}
    )
    missing = workshop.client.post(f"{booked.page}/reschedule", json={})

    assert closed.status_code == 422, closed.text
    assert reasons(closed) == ["closed"]
    assert missing.status_code == 422, missing.text
    still: JsonObject = workshop.client.get(booked.page).json()
    assert (still["date"], still["time"]) == ("2026-10-06", "19:00")


def test_a_guest_cancels_once_and_the_page_says_so(workshop: Workshop) -> None:
    booked = book_a_table(workshop)

    cancelled = workshop.client.post(f"{booked.page}/cancel")

    assert cancelled.status_code == 200, cancelled.text
    view: JsonObject = cancelled.json()
    assert (view["status"], view["can_cancel"], view["can_reschedule"]) == (
        "cancelled",
        False,
        False,
    )
    # The same link still opens the page; a second cancel changes nothing.
    again = workshop.client.post(f"{booked.page}/cancel")
    assert again.status_code == 200
    assert again.json()["status"] == "cancelled"
    move = workshop.client.post(
        f"{booked.page}/reschedule", json={"date": NEXT_DAY, "time": "20:00"}
    )
    assert move.status_code == 409
    assert reasons(move) == ["not_active"]
    calendar = workshop.client.get(f"{booked.page}/calendar.ics")
    assert "STATUS:CANCELLED" in calendar.text
    # Staff see the cancellation in the cabinet.
    listed = workshop.client.get(
        f"{booked.restaurant.base}/bookings", headers=booked.restaurant.headers
    ).json()["items"]
    assert [item["status"] for item in listed] == ["cancelled"]


def test_a_started_booking_cannot_change(workshop: Workshop) -> None:
    booked = book_a_table(workshop)
    workshop.clock.advance(UNTIL_THE_VISIT_STARTED)

    page: JsonObject = workshop.client.get(booked.page).json()
    cancelled = workshop.client.post(f"{booked.page}/cancel")

    assert (page["can_cancel"], page["can_reschedule"], page["is_over"]) == (
        False,
        False,
        False,
    )
    assert cancelled.status_code == 409
    assert reasons(cancelled) == ["already_started"]


def test_two_moves_through_one_link_cannot_both_win(workshop: Workshop) -> None:
    booked = book_a_table(workshop)
    operator = workshop.container.operators.booking_links
    reschedule = operator.reschedule_managed_booking_operator()
    start = threading.Barrier(2)
    outcomes: dict[str, ManagedBookingView | ApplicationError] = {}

    def move(time: str) -> None:
        request = ManagedBookingRequest(
            token=BookingManageToken(booked.token),
            date=LocalDate(NEXT_DAY),
            time=LocalTimeOfDay(time),
        )
        start.wait()
        try:
            outcomes[time] = reschedule.operate(request)
        except ApplicationError as error:
            outcomes[time] = error

    threads = [
        threading.Thread(target=move, args=(time,)) for time in ("18:00", "21:00")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    moved = [
        time
        for time, outcome in outcomes.items()
        if not isinstance(outcome, ApplicationError)
    ]
    refused = [
        outcome
        for outcome in outcomes.values()
        if isinstance(outcome, ApplicationError)
    ]
    assert len(moved) == 1 and len(refused) == 1, outcomes
    assert [str(reason.code) for reason in refused[0].reasons] == ["booking_changed"]
    page = workshop.client.get(f"{BOOKINGS_PATH}/{_token_of(outcomes, moved[0])}")
    assert page.json()["time"] == moved[0]


def _token_of(
    outcomes: dict[str, ManagedBookingView | ApplicationError], time: str
) -> str:
    outcome = outcomes[time]
    assert isinstance(outcome, ManagedBookingView)
    return str(outcome.token)


def test_free_times_are_limited_per_link(workshop: Workshop) -> None:
    booked = book_a_table(workshop)

    answers = [
        workshop.client.get(f"{booked.page}/slots", params={"date": NEXT_DAY})
        for _ in range(31)
    ]

    assert [answer.status_code for answer in answers[:30]] == [200] * 30
    assert answers[30].status_code == 429
    assert int(answers[30].headers["retry-after"]) > 0
    # The page itself counts apart and still opens.
    assert workshop.client.get(booked.page).status_code == 200
