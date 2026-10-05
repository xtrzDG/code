from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingUnit
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.booking_manage import ManagedBookingAction, ManagedBookingSlots
from app.schemas.dto.bookings import AvailabilityQuery, AvailabilityResult
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    NightCount,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.use_cases.bookings.guest_booking import GuestBooking
from app.use_cases.bookings.public.managed_booking_pages import ManagedBookingPages
from app.utilities.bookings.manage_rate_limits import MANAGE_SLOT_LIMITS
from app.utilities.scheduling.zoned_time import load_time_zone, to_local_moment

SECONDS_PER_MINUTE: int = 60
DATE_REQUIRED_MESSAGE: str = "Give the date to look for free times on."


class FindManagedBookingSlotsUseCase(
    UseCaseContract[ManagedBookingAction, ManagedBookingSlots]
):
    """
    Where the guest could move their booking on one local date, through
    `check_availability` with the booking as it is: its service (or the
    kind of its place and its length), its party and, for a stay, its
    number of nights, by the rules customers book by (minimum notice,
    online party size). Every free start time of the date is listed, and
    the booking does not block its own time. Only a booking the guest may
    still change is looked up.
    """

    def __init__(
        self,
        pages: ManagedBookingPages,
        check_availability: UseCaseContract[AvailabilityQuery, AvailabilityResult],
    ) -> None:
        self._pages: ManagedBookingPages = pages
        self._check_availability: UseCaseContract[
            AvailabilityQuery, AvailabilityResult
        ] = check_availability

    def run(self, input_data: ManagedBookingAction) -> ManagedBookingSlots:
        self._pages.refuse_too_frequent(input_data, MANAGE_SLOT_LIMITS)
        if input_data.date is None:
            raise ValidationFailedError(DATE_REQUIRED_MESSAGE)

        guest_booking: GuestBooking = self._pages.current(input_data.claims)
        self._pages.refuse_unchangeable(guest_booking.booking)
        result: AvailabilityResult = self._check_availability.run(
            build_query(guest_booking, input_data.date)
        )
        times: list[LocalTimeOfDay] = sorted(
            {
                slot.time
                for slot in result.slots
                if slot.booking_unit is BookingUnit.TIME_SLOT and slot.time is not None
            },
            key=str,
        )
        return ManagedBookingSlots(
            date=input_data.date,
            timezone=result.timezone,
            booking_unit=guest_booking.booking_unit,
            is_open_on_date=result.is_open_on_date,
            times=times,
            is_stay_available=any(
                slot.booking_unit is BookingUnit.NIGHT for slot in result.slots
            ),
        )


def build_query(guest_booking: GuestBooking, date: LocalDate) -> AvailabilityQuery:
    """The availability question of moving this booking to `date`."""

    booking: BookingDocument = guest_booking.booking
    resource: ResourceDocument | None = guest_booking.resource
    is_stay: bool = guest_booking.booking_unit is BookingUnit.NIGHT
    has_service: bool = booking.service_item_id is not None
    return AvailabilityQuery(
        business_id=booking.business_id,
        date=date,
        service_item_id=booking.service_item_id,
        resource_kind=None if has_service or resource is None else resource.kind,
        party_size=booking.party_size,
        duration_minutes=(
            None
            if is_stay or has_service
            else BookingDurationMinutes(
                (int(booking.ends_at) - int(booking.starts_at)) // SECONDS_PER_MINUTE
            )
        ),
        nights=stay_nights(guest_booking) if is_stay else None,
        is_sandbox=False,
        lists_every_time=True,
        excluded_booking_id=booking.id,
    )


def stay_nights(guest_booking: GuestBooking) -> NightCount:
    zone = load_time_zone(guest_booking.business.timezone)
    booking = guest_booking.booking
    check_in = to_local_moment(int(booking.starts_at), zone).date()
    check_out = to_local_moment(int(booking.ends_at), zone).date()
    return NightCount(max((check_out - check_in).days, 1))
