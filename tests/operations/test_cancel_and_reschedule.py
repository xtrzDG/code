from datetime import datetime

import pytest

from app.schemas.constants.bookings import BookingStatus, BookingUnit, ResourceKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.bookings import CancelBookingCommand, RescheduleBookingCommand
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from tests.operations.builders import OperationsWorld

PHONE: str = "+995555123456"


def seconds(text: str) -> int:
    return int(datetime.fromisoformat(text).timestamp())


class BookedRestaurant:
    """Tbilisi restaurant where two customers already booked."""

    def __init__(self) -> None:
        self.world = OperationsWorld()
        self.business = self.world.add_business()
        self.world.add_profile(self.business)
        self.world.add_resource(self.business, "Table 2", capacity=2)
        self.table_for_four = self.world.add_resource(
            self.business, "Table 4", capacity=4
        )
        self.table_for_eight = self.world.add_resource(
            self.business, "Table 8", capacity=8
        )
        self.customer = self.world.add_contact(self.business, "Giorgi", PHONE)
        self.other_customer = self.world.add_contact(
            self.business, "Tamar", "+995599765432"
        )
        self.dinner: BookingDocument = self.world.add_booking(
            self.business,
            self.table_for_four,
            self.customer,
            "2026-10-06T19:00:00+04:00",
            "2026-10-06T21:00:00+04:00",
            party_size=4,
        )
        self.lunch: BookingDocument = self.world.add_booking(
            self.business,
            self.table_for_four,
            self.customer,
            "2026-10-08T13:00:00+04:00",
            "2026-10-08T15:00:00+04:00",
            party_size=4,
        )
        self.other_dinner: BookingDocument = self.world.add_booking(
            self.business,
            self.table_for_eight,
            self.other_customer,
            "2026-10-06T19:00:00+04:00",
            "2026-10-06T21:00:00+04:00",
            party_size=6,
        )

    def cancel(
        self,
        booking_id: BookingId | None = None,
        contact_id: ContactId | None = None,
        phone: str | None = None,
        day: str | None = None,
        language: str = "ru",
    ) -> str:
        result = self.world.cancel_booking().run(
            CancelBookingCommand(
                business_id=self.business.id,
                booking_id=booking_id,
                contact_id=contact_id,
                contact_phone_number=None if phone is None else E164PhoneNumber(phone),
                date=None if day is None else LocalDate(day),
                language=LanguageTag(language),
            )
        )
        return str(result.confirmation_text)

    def reschedule(
        self,
        new_date: str,
        new_time: str | None,
        booking_id: BookingId | None = None,
        contact_id: ContactId | None = None,
        old_date: str | None = None,
        language: str = "en",
    ) -> str:
        result = self.world.reschedule_booking().run(
            RescheduleBookingCommand(
                business_id=self.business.id,
                booking_id=booking_id,
                contact_id=contact_id,
                old_date=None if old_date is None else LocalDate(old_date),
                new_date=LocalDate(new_date),
                new_time=None if new_time is None else LocalTimeOfDay(new_time),
                language=LanguageTag(language),
            )
        )
        return str(result.confirmation_text)

    def stored(self, booking: BookingDocument) -> BookingDocument:
        found = self.world.booking_repo.get(self.business.id, booking.id)
        assert found is not None
        return found


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


class TestReschedule:
    def test_customer_moves_a_booking_keeping_its_length(self) -> None:
        restaurant = BookedRestaurant()

        text = restaurant.reschedule(
            "2026-10-07",
            "20:00",
            contact_id=restaurant.customer.id,
            old_date="2026-10-06",
        )

        moved = restaurant.stored(restaurant.dinner)
        assert moved.resource_id == restaurant.table_for_four.id
        assert int(moved.starts_at) == seconds("2026-10-07T20:00:00+04:00")
        assert int(moved.ends_at) == seconds("2026-10-07T22:00:00+04:00")
        assert "has been moved to Wednesday, October 7, 2026, 20:00" in text
        assert "Cancellation policy:" in text
        assert any(
            str(message).startswith("Booking moved to a new time")
            for _, message in restaurant.world.notifier.sent
        )
        assert restaurant.world.calendar_sync.synced[-1].id == restaurant.dinner.id

    def test_overlapping_only_itself_is_allowed(self) -> None:
        restaurant = BookedRestaurant()

        restaurant.reschedule("2026-10-06", "19:30", booking_id=restaurant.dinner.id)

        assert int(restaurant.stored(restaurant.dinner).starts_at) == seconds(
            "2026-10-06T19:30:00+04:00"
        )

    def test_taken_table_moves_to_a_free_one_of_the_same_kind(self) -> None:
        restaurant = BookedRestaurant()

        with pytest.raises(ConflictError):
            restaurant.reschedule("2026-10-06", "19:00", booking_id=restaurant.lunch.id)

        restaurant.cancel(booking_id=restaurant.other_dinner.id)
        restaurant.reschedule("2026-10-06", "19:00", booking_id=restaurant.lunch.id)

        assert restaurant.stored(restaurant.lunch).resource_id == (
            restaurant.table_for_eight.id
        )

    def test_rules_for_customers_and_staff(self) -> None:
        restaurant = BookedRestaurant()

        with pytest.raises(ValidationFailedError, match="new time"):
            restaurant.reschedule("2026-10-07", None, booking_id=restaurant.dinner.id)

        # Now is 12:00 local: customers need an hour of notice, staff do not.
        with pytest.raises(ValidationFailedError, match="too soon"):
            restaurant.reschedule(
                "2026-10-05",
                "12:30",
                booking_id=restaurant.dinner.id,
                contact_id=restaurant.customer.id,
            )

        restaurant.reschedule("2026-10-05", "12:30", booking_id=restaurant.dinner.id)
        assert restaurant.world.notifier.sent == []

        restaurant.cancel(booking_id=restaurant.lunch.id)
        with pytest.raises(ConflictError, match="cancelled"):
            restaurant.reschedule("2026-10-09", "13:00", booking_id=restaurant.lunch.id)

    def test_stay_keeps_its_number_of_nights(self) -> None:
        world = OperationsWorld()
        hotel = world.add_business(
            name="Guesthouse Ararat",
            country_code="AM",
            timezone="Asia/Yerevan",
            currency_code="AMD",
            languages=("hy", "ru", "en"),
            owner_language="hy",
        )
        world.add_profile(hotel, resource_kind=ResourceKind.ROOM)
        room = world.add_resource(
            hotel,
            "Family room",
            capacity=4,
            kind=ResourceKind.ROOM,
            booking_unit=BookingUnit.NIGHT,
        )
        guest = world.add_contact(hotel, "Aram", "+37491123456")
        stay = world.add_booking(
            hotel,
            room,
            guest,
            "2026-10-12T14:00:00+04:00",
            "2026-10-15T12:00:00+04:00",
        )

        result = world.reschedule_booking().run(
            RescheduleBookingCommand(
                business_id=hotel.id,
                contact_phone_number=E164PhoneNumber("+37491123456"),
                old_date=LocalDate("2026-10-12"),
                new_date=LocalDate("2026-10-20"),
                language=LanguageTag("hy"),
            )
        )

        moved = world.booking_repo.get(hotel.id, stay.id)
        assert moved is not None
        assert int(moved.starts_at) == seconds("2026-10-20T14:00:00+04:00")
        assert int(moved.ends_at) == seconds("2026-10-23T12:00:00+04:00")
        assert "տեղափոխվել է" in str(result.confirmation_text)
        assert (result.booking.end_date, result.booking.end_time) == (
            "2026-10-23",
            "12:00",
        )
