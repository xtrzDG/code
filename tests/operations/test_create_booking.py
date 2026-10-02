"""Creating a booking: confirmation, contact, notices, conflicts and limits."""

import threading

import pytest

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from tests.operations.builders import seconds
from tests.operations.fakes import RecordingManagerNotifier
from tests.operations.operations_world import OperationsWorld
from tests.operations.restaurant_booking_fixture import Restaurant


def test_booking_is_confirmed_with_a_georgian_confirmation() -> None:
    restaurant = Restaurant()

    result = restaurant.book(restaurant.command())

    view = result.booking
    assert view.status is BookingStatus.CONFIRMED
    assert view.resource_name == "Table 4"
    assert (view.date, view.time, view.end_date, view.end_time) == (
        "2026-10-06",
        "19:00",
        "2026-10-06",
        "21:00",
    )
    assert view.timezone == "Asia/Tbilisi"
    assert view.contact_name == "Giorgi Beridze"
    assert view.contact_phone_number == "+995555123456"
    stored = restaurant.world.bookings_of(restaurant.business.id)
    assert len(stored) == 1
    assert int(stored[0].starts_at) == seconds("2026-10-06T19:00:00+04:00")
    assert int(stored[0].ends_at) == seconds("2026-10-06T21:00:00+04:00")
    assert stored[0].notes == "Window seat"
    text = str(result.confirmation_text)
    assert "დადასტურებულია" in text
    assert "ოქტომბერი" in text
    assert "19:00" in text and "Giorgi Beridze" in text and ": 4." in text


def test_contact_details_are_updated_and_audited() -> None:
    restaurant = Restaurant()

    restaurant.book(restaurant.command())

    contact = restaurant.world.contact_repo.get(
        restaurant.business.id, restaurant.contact.id
    )
    assert contact is not None
    assert (contact.name, contact.phone_number) == ("Giorgi Beridze", "+995555123456")
    entries = restaurant.world.audit_repo.list_by_business(restaurant.business.id)
    assert [(entry.action, entry.entity, entry.actor_id) for entry in entries] == [
        (AuditAction.UPDATE, "contact", None)
    ]


def test_every_manager_is_notified_in_their_language() -> None:
    restaurant = Restaurant()

    restaurant.book(restaurant.command())

    texts = {
        str(contact.language): str(text)
        for contact, text in restaurant.world.notifier.sent
    }
    assert set(texts) == {"ka", "ru", "en"}
    assert texts["ka"].startswith("ახალი ჯავშანი · Salobie Bia")
    assert texts["ru"].startswith("Новая бронь · Salobie Bia")
    assert "Телефон: +995 555 12 34 56" in texts["ru"]
    assert "Пожелания: Window seat" in texts["ru"]
    # E-mail gets the brief: when and how many, nothing about the customer.
    assert texts["en"] == (
        "New booking · Salobie Bia\nTuesday, October 6, 2026, 19:00–21:00 · guests: 4"
    )
    assert "Phone" not in texts["en"] and "Window seat" not in texts["en"]
    assert restaurant.world.calendar_sync.synced[0].id == (
        restaurant.world.bookings_of(restaurant.business.id)[0].id
    )


def test_sandbox_booking_notifies_nobody_and_skips_the_calendar() -> None:
    restaurant = Restaurant()

    result = restaurant.book(restaurant.command(is_sandbox=True))

    assert result.booking.is_sandbox
    assert restaurant.world.notifier.sent == []
    assert restaurant.world.calendar_sync.synced == []


def test_failing_notifier_never_breaks_the_booking() -> None:
    world = OperationsWorld()
    world.notifier = RecordingManagerNotifier(
        failing_addresses=frozenset({"+995555000111"}),
        raising_addresses=frozenset({"4242"}),
    )
    world.rebuild_staff_alerts()
    restaurant = Restaurant(world)

    result = restaurant.book(restaurant.command())

    assert result.booking.status is BookingStatus.CONFIRMED
    assert [str(contact.address) for contact, _ in world.notifier.sent] == [
        "+995555000111",
        "anna@example.com",
    ]


def test_taken_last_unit_raises_conflict() -> None:
    restaurant = Restaurant()
    restaurant.book(restaurant.command(party_size=6))

    with pytest.raises(ConflictError, match="already booked"):
        restaurant.book(restaurant.command(party_size=6))

    # A smaller party still gets a smaller table at the same time.
    assert restaurant.book(restaurant.command(party_size=2)).booking.resource_name == (
        "Table 2"
    )


def test_concurrent_requests_for_the_last_unit_book_it_once() -> None:
    restaurant = Restaurant()
    use_case = restaurant.world.create_booking()
    barrier = threading.Barrier(8)
    outcomes: list[str] = []
    outcomes_lock = threading.Lock()

    def attempt() -> None:
        barrier.wait()
        try:
            use_case.run(restaurant.command(party_size=8, language="en"))
            outcome = "booked"
        except ConflictError:
            outcome = "conflict"

        with outcomes_lock:
            outcomes.append(outcome)

    threads = [threading.Thread(target=attempt) for _ in range(8)]
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["booked"] + ["conflict"] * 7
    assert len(restaurant.world.bookings_of(restaurant.business.id)) == 1


@pytest.mark.parametrize(
    ("time", "day", "message"),
    [
        ("23:30", "2026-10-06", "closed"),
        ("11:00", "2026-10-06", "closed"),
        ("12:30", "2026-10-05", "too soon"),
        (None, "2026-10-06", "time is required"),
    ],
)
def test_invalid_times_are_refused(time: str | None, day: str, message: str) -> None:
    restaurant = Restaurant()

    with pytest.raises(ValidationFailedError, match=message):
        restaurant.book(restaurant.command(time=time, day=day))

    assert restaurant.world.bookings_of(restaurant.business.id) == []


def test_party_limits_and_unknown_contact() -> None:
    restaurant = Restaurant()

    with pytest.raises(ValidationFailedError, match="12 guests"):
        restaurant.book(restaurant.command(party_size=20))

    with pytest.raises(ValidationFailedError, match="No bookable resource"):
        restaurant.book(restaurant.command(party_size=10))

    with pytest.raises(NotFoundError):
        restaurant.book(restaurant.command(contact_id=ContactId()))


def test_unsupported_language_falls_back_to_english_and_regional_to_base() -> None:
    restaurant = Restaurant()

    portuguese = restaurant.book(restaurant.command(language="pt-BR", time="13:00"))
    russian = restaurant.book(restaurant.command(language="ru-RU", time="16:00"))

    assert str(portuguese.confirmation_text).startswith("Your booking at Salobie Bia")
    assert "October 6, 2026" in str(portuguese.confirmation_text)
    assert str(russian.confirmation_text).startswith("Ваша бронь в «Salobie Bia»")
    assert "6 октября 2026" in str(russian.confirmation_text)
