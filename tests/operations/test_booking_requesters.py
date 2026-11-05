"""
Who may cancel or move a booking: staff (the cabinet's user) any booking by
its id; a customer only their own and never from a phone call; a command
naming neither is refused instead of getting staff authority. Customers
book at most the horizon ahead.
"""

import pytest

from app.schemas.constants.channels import ChannelKind
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
    ValidationFailedError,
)
from app.use_cases.bookings.booking_limits import MAX_BOOKING_HORIZON_DAYS
from tests.operations.booked_restaurant import BookedRestaurant


def test_a_booking_id_alone_never_gets_staff_authority() -> None:
    restaurant = BookedRestaurant()

    with pytest.raises(AccessDeniedError, match="names neither"):
        restaurant.cancel(booking_id=restaurant.dinner.id, as_staff=False)
    with pytest.raises(AccessDeniedError, match="names neither"):
        restaurant.reschedule(
            "2026-10-06", "19:30", booking_id=restaurant.dinner.id, as_staff=False
        )

    assert restaurant.stored(restaurant.dinner).status.value == "confirmed"


def test_staff_change_any_booking_of_the_business_by_its_id() -> None:
    restaurant = BookedRestaurant()

    restaurant.reschedule("2026-10-06", "19:30", booking_id=restaurant.other_dinner.id)
    restaurant.cancel(booking_id=restaurant.other_dinner.id)

    assert restaurant.stored(restaurant.other_dinner).status.value == "cancelled"
    # A cabinet change notifies no staff.
    assert restaurant.world.notifier.sent == []


def test_a_customer_reaches_only_their_own_booking() -> None:
    restaurant = BookedRestaurant()

    with pytest.raises(NotFoundError):
        restaurant.cancel(
            booking_id=restaurant.other_dinner.id, contact_id=restaurant.customer.id
        )


@pytest.mark.parametrize("action", ["cancel", "reschedule"])
def test_a_caller_id_does_not_change_a_booking(action: str) -> None:
    restaurant = BookedRestaurant()

    with pytest.raises(AccessDeniedError, match="does not prove who is calling"):
        if action == "cancel":
            restaurant.cancel(
                contact_id=restaurant.customer.id,
                day="2026-10-06",
                channel=ChannelKind.PHONE,
            )
        else:
            restaurant.reschedule(
                "2026-10-07",
                "20:00",
                contact_id=restaurant.customer.id,
                old_date="2026-10-06",
                channel=ChannelKind.PHONE,
            )

    assert restaurant.stored(restaurant.dinner).status.value == "confirmed"


def test_customers_cannot_move_a_booking_past_the_horizon() -> None:
    restaurant = BookedRestaurant()

    with pytest.raises(ValidationFailedError, match=f"{MAX_BOOKING_HORIZON_DAYS} days"):
        restaurant.reschedule(
            "2027-12-01",
            "20:00",
            contact_id=restaurant.customer.id,
            old_date="2026-10-06",
        )
