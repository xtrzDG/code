"""Moving a booking: length kept, free tables, rules and stays."""

import pytest

from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.dto.bookings import RescheduleBookingCommand
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from tests.operations.booked_restaurant import BookedRestaurant
from tests.operations.builders import seconds
from tests.operations.operations_world import OperationsWorld


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
            str(message).startswith(
                ("Booking moved to a new time", "Booking moved · ")
            )
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
