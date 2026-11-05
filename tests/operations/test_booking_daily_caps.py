"""
How often and how far ahead customers book: a contact's daily cap, the
caps of anonymous bookings per client network and per business, and the
booking horizon; an owner's test counts against none of them. A place
held for an unpaid deposit stays taken until the deposit sweep releases
it.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deposits import DepositStatus
from app.schemas.domain.deposits import BookingDeposit
from app.schemas.dto.bookings import AvailabilityQuery, CreateBookingCommand
from app.schemas.exceptions.application_errors import (
    ConflictError,
    RateLimitedError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.deposits.constrained_integers import DepositDueMinor
from app.schemas.typings.deposits.prefixed_id import DepositRequestId
from app.use_cases.bookings import booking_limits
from app.use_cases.bookings.booking_limits import (
    MAX_ANONYMOUS_BOOKINGS_PER_NETWORK_PER_DAY,
    MAX_BOOKING_HORIZON_DAYS,
    MAX_BOOKINGS_PER_CONTACT_PER_DAY,
)
from tests.operations.restaurant_booking_fixture import Restaurant

DAYS: list[str] = [f"2026-10-{day:02d}" for day in range(6, 30)]


def booking_on(
    restaurant: Restaurant, day: str, **changes: object
) -> CreateBookingCommand:
    return restaurant.command(day=day).model_copy(update=changes)


def test_a_contact_makes_a_handful_of_bookings_a_day() -> None:
    restaurant = Restaurant()
    for day in DAYS[:MAX_BOOKINGS_PER_CONTACT_PER_DAY]:
        restaurant.book(booking_on(restaurant, day))

    with pytest.raises(RateLimitedError, match="Too many bookings"):
        restaurant.book(booking_on(restaurant, DAYS[MAX_BOOKINGS_PER_CONTACT_PER_DAY]))

    # The refused one was not saved; an owner's test still books.
    stored = restaurant.world.booking_repo.list_by_business(restaurant.business.id)
    assert len(stored) == MAX_BOOKINGS_PER_CONTACT_PER_DAY
    restaurant.book(
        booking_on(restaurant, DAYS[MAX_BOOKINGS_PER_CONTACT_PER_DAY], is_sandbox=True)
    )


def test_a_taken_time_costs_nothing() -> None:
    restaurant = Restaurant()
    restaurant.book(booking_on(restaurant, DAYS[0], party_size=8))
    for _ in range(MAX_BOOKINGS_PER_CONTACT_PER_DAY):
        with pytest.raises(ConflictError):
            restaurant.book(booking_on(restaurant, DAYS[0], party_size=8))

    restaurant.book(booking_on(restaurant, DAYS[1]))


def test_anonymous_bookings_are_capped_per_client_network() -> None:
    restaurant = Restaurant()
    address = ClientIpAddress("203.0.113.7")
    for index in range(MAX_ANONYMOUS_BOOKINGS_PER_NETWORK_PER_DAY):
        contact = restaurant.world.add_contact(restaurant.business)
        restaurant.book(
            booking_on(
                restaurant,
                DAYS[index],
                contact_id=contact.id,
                source_channel=ChannelKind.WEB_CHAT,
                client_ip_address=address,
            )
        )

    stranger = restaurant.world.add_contact(restaurant.business)
    with pytest.raises(RateLimitedError):
        restaurant.book(
            booking_on(
                restaurant,
                DAYS[-1],
                contact_id=stranger.id,
                source_channel=ChannelKind.WEB_CHAT,
                client_ip_address=address,
            )
        )
    # Another network is not held up.
    restaurant.book(
        booking_on(
            restaurant,
            DAYS[-1],
            contact_id=stranger.id,
            source_channel=ChannelKind.WEB_CHAT,
            client_ip_address=ClientIpAddress("198.51.100.20"),
        )
    )


def test_anonymous_bookings_are_capped_per_business(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Two a day stand in for the real cap; a caller id is anonymous too.
    monkeypatch.setattr(
        booking_limits, "MAX_ANONYMOUS_BOOKINGS_PER_BUSINESS_PER_DAY", 2
    )
    restaurant = Restaurant()
    for index in range(2):
        caller = restaurant.world.add_contact(restaurant.business)
        restaurant.book(
            booking_on(
                restaurant,
                DAYS[index],
                contact_id=caller.id,
                source_channel=ChannelKind.PHONE,
            )
        )

    stranger = restaurant.world.add_contact(restaurant.business)
    with pytest.raises(RateLimitedError):
        restaurant.book(
            booking_on(
                restaurant,
                DAYS[2],
                contact_id=stranger.id,
                source_channel=ChannelKind.WEB_CHAT,
            )
        )
    # A customer of a messenger proves their account: not held up.
    restaurant.book(booking_on(restaurant, DAYS[2], contact_id=stranger.id))


def test_customers_book_at_most_the_horizon_ahead() -> None:
    restaurant = Restaurant()

    with pytest.raises(ValidationFailedError, match=f"{MAX_BOOKING_HORIZON_DAYS} days"):
        restaurant.book(booking_on(restaurant, "2027-10-06"))
    with pytest.raises(ValidationFailedError, match=f"{MAX_BOOKING_HORIZON_DAYS} days"):
        restaurant.world.check_availability().run(
            AvailabilityQuery(
                business_id=restaurant.business.id, date=LocalDate("2027-10-06")
            )
        )

    # Staff see any day in the cabinet.
    staff_view = restaurant.world.check_availability().run(
        AvailabilityQuery(
            business_id=restaurant.business.id,
            date=LocalDate("2027-10-06"),
            full_day=True,
        )
    )
    assert staff_view.timezone == restaurant.business.timezone


@pytest.mark.parametrize("hold_ends_in_seconds", [-60, 600])
def test_a_place_held_for_a_deposit_stays_taken_until_the_hold_is_released(
    hold_ends_in_seconds: int,
) -> None:
    # Only the deposit sweep frees a lapsed hold, under the business lock and
    # against "Paid": a place freed earlier could be booked twice when staff
    # mark the late deposit paid.
    restaurant = Restaurant()
    held = restaurant.book(booking_on(restaurant, DAYS[0], party_size=8)).booking
    stored = restaurant.world.booking_repo.get(restaurant.business.id, held.id)
    assert stored is not None
    now = int(restaurant.world.clock.wall_clock.now_unix())
    stored.status = BookingStatus.PENDING
    stored.deposit_status = DepositStatus.AWAITING
    stored.deposit = BookingDeposit(
        request_id=DepositRequestId(),
        status=DepositStatus.AWAITING,
        amount_minor=DepositDueMinor(2000),
        currency_code=restaurant.business.currency_code,
        hold_expires_at=Microseconds(now + hold_ends_in_seconds * 1_000_000),
    )
    restaurant.world.booking_repo.save(stored)
    other = restaurant.world.add_contact(restaurant.business)

    with pytest.raises(ConflictError):
        restaurant.book(
            booking_on(restaurant, DAYS[0], party_size=8, contact_id=other.id)
        )
