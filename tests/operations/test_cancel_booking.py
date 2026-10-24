"""Cancelling a booking: lookups, policy, notices, calendar and sandbox isolation."""

import pytest

from app.schemas.constants.bookings import BookingStatus
from app.schemas.dto.bookings import CancelBookingCommand, RescheduleBookingCommand
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from tests.operations.booked_restaurant import PHONE, BookedRestaurant


class TestCancel:
    def test_customer_cancels_by_id_with_policy_and_staff_notice(self) -> None:
        restaurant = BookedRestaurant()

        text = restaurant.cancel(
            booking_id=restaurant.dinner.id, contact_id=restaurant.customer.id
        )

        assert restaurant.stored(restaurant.dinner).status is BookingStatus.CANCELLED
        assert text.startswith("Ваша бронь в «Salobie Bia» на вторник, 6 октября 2026")
        assert "19:00 отменена." in text
        assert "Правила отмены: Free cancellation up to 2 hours before." in text
        titles = sorted(
            str(text).split("\n")[0] for _, text in restaurant.world.notifier.sent
        )
        assert titles == [
            "Booking cancelled · Salobie Bia",
            "Бронь отменена · Salobie Bia",
            "ჯავშანი გაუქმდა · Salobie Bia",
        ]
        assert [booking.id for booking in restaurant.world.calendar_sync.synced] == [
            restaurant.dinner.id
        ]

    def test_someone_elses_booking_is_not_found(self) -> None:
        restaurant = BookedRestaurant()

        with pytest.raises(NotFoundError):
            restaurant.cancel(
                booking_id=restaurant.other_dinner.id,
                contact_id=restaurant.customer.id,
            )

        assert restaurant.stored(restaurant.other_dinner).status is (
            BookingStatus.CONFIRMED
        )

    def test_by_phone_and_date_across_contacts_of_the_same_person(self) -> None:
        restaurant = BookedRestaurant()
        # The same person also wrote from Instagram (a second contact).
        instagram_contact = restaurant.world.add_contact(
            restaurant.business, "Giorgi", PHONE
        )

        restaurant.cancel(
            contact_id=instagram_contact.id, phone=PHONE, day="2026-10-06"
        )

        assert restaurant.stored(restaurant.dinner).status is BookingStatus.CANCELLED
        assert restaurant.stored(restaurant.lunch).status is BookingStatus.CONFIRMED

    def test_ambiguous_missing_and_anonymous_lookups(self) -> None:
        restaurant = BookedRestaurant()

        with pytest.raises(ConflictError, match="2 bookings match"):
            restaurant.cancel(contact_id=restaurant.customer.id)

        with pytest.raises(NotFoundError):
            restaurant.cancel(contact_id=restaurant.customer.id, day="2026-10-09")

        with pytest.raises(ValidationFailedError):
            restaurant.cancel()

        with pytest.raises(NotFoundError):
            restaurant.cancel(booking_id=BookingId())

    def test_cancelling_twice_is_harmless_and_finished_bookings_stay(self) -> None:
        restaurant = BookedRestaurant()
        restaurant.cancel(
            booking_id=restaurant.dinner.id, contact_id=restaurant.customer.id
        )
        notifications = len(restaurant.world.notifier.sent)

        again = restaurant.cancel(
            booking_id=restaurant.dinner.id, contact_id=restaurant.customer.id
        )

        assert "отменена" in again
        assert len(restaurant.world.notifier.sent) == notifications
        completed = restaurant.stored(restaurant.lunch)
        completed.status = BookingStatus.COMPLETED
        restaurant.world.booking_repo.save(completed)
        with pytest.raises(ConflictError, match="completed"):
            restaurant.cancel(booking_id=restaurant.lunch.id)

    def test_cabinet_cancel_syncs_calendar_without_staff_notice(self) -> None:
        restaurant = BookedRestaurant()

        text = restaurant.cancel(booking_id=restaurant.dinner.id, language="ka")

        assert "გაუქმებულია" in text
        assert restaurant.world.notifier.sent == []
        assert len(restaurant.world.calendar_sync.synced) == 1

    def test_sandbox_cancel_touches_no_staff_and_no_calendar(self) -> None:
        restaurant = BookedRestaurant()
        test_booking = restaurant.world.add_booking(
            restaurant.business,
            restaurant.table_for_eight,
            restaurant.customer,
            "2026-10-09T19:00:00+04:00",
            "2026-10-09T21:00:00+04:00",
            is_sandbox=True,
        )

        restaurant.cancel(booking_id=test_booking.id, contact_id=restaurant.customer.id)

        assert restaurant.world.notifier.sent == []
        assert restaurant.world.calendar_sync.synced == []

    def test_an_owner_test_never_reaches_a_real_booking(self) -> None:
        restaurant = BookedRestaurant()
        tester = restaurant.world.add_contact(restaurant.business, "Owner", PHONE)

        for command in (
            CancelBookingCommand(
                business_id=restaurant.business.id,
                contact_id=tester.id,
                contact_phone_number=E164PhoneNumber(PHONE),
                date=LocalDate("2026-10-06"),
                language=LanguageTag("en"),
                is_sandbox=True,
            ),
            CancelBookingCommand(
                business_id=restaurant.business.id,
                contact_id=tester.id,
                booking_id=restaurant.dinner.id,
                contact_phone_number=E164PhoneNumber(PHONE),
                language=LanguageTag("en"),
                is_sandbox=True,
            ),
        ):
            with pytest.raises(NotFoundError):
                restaurant.world.cancel_booking().run(command)

        with pytest.raises(NotFoundError):
            restaurant.world.reschedule_booking().run(
                RescheduleBookingCommand(
                    business_id=restaurant.business.id,
                    contact_id=tester.id,
                    contact_phone_number=E164PhoneNumber(PHONE),
                    old_date=LocalDate("2026-10-06"),
                    new_date=LocalDate("2026-10-07"),
                    new_time=LocalTimeOfDay("20:00"),
                    language=LanguageTag("en"),
                    is_sandbox=True,
                )
            )

        assert restaurant.stored(restaurant.dinner).status is BookingStatus.CONFIRMED
        assert restaurant.world.notifier.sent == []
        assert restaurant.world.calendar_sync.synced == []

    def test_a_real_customer_never_reaches_a_test_booking(self) -> None:
        restaurant = BookedRestaurant()
        test_booking = restaurant.world.add_booking(
            restaurant.business,
            restaurant.table_for_eight,
            restaurant.customer,
            "2026-10-09T19:00:00+04:00",
            "2026-10-09T21:00:00+04:00",
            is_sandbox=True,
        )

        with pytest.raises(NotFoundError):
            restaurant.world.cancel_booking().run(
                CancelBookingCommand(
                    business_id=restaurant.business.id,
                    contact_id=restaurant.customer.id,
                    contact_phone_number=E164PhoneNumber(PHONE),
                    date=LocalDate("2026-10-09"),
                    language=LanguageTag("en"),
                    is_sandbox=False,
                )
            )

        assert restaurant.stored(test_booking).status is BookingStatus.CONFIRMED
