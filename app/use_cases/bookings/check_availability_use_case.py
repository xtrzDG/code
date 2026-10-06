from datetime import date

from typed_time_provider import Microseconds, WallClock

from app.contracts.calendar_sync import (
    BusyTimeSyncFacilitatorContract,
    CalendarBusyTimesRepoContract,
)
from app.contracts.growth import GrowthBookingsFacilitatorContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
    ScheduleExceptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import (
    AvailabilityQuery,
    AvailabilityResult,
    AvailableSlot,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.use_cases.bookings.availability_slots import (
    StayPricing,
    all_time_slots,
    free_stays,
    is_open_for,
    nearest_time_slots,
)
from app.use_cases.bookings.booking_support import (
    SchedulingInputs,
    load_scheduling_inputs,
)
from app.use_cases.bookings.bookings_in_play import HeldPlaces, bookings_not_over_on
from app.use_cases.bookings.offer_selection import (
    OfferChoice,
    OfferRequest,
    choose_offer,
)
from app.utilities.bookings.offer_views import build_offer_view, list_offer_views
from app.utilities.calendar_sync.busy_windows import ON_DEMAND_READ_SECONDS
from app.utilities.scheduling.placement_request import PlacementRequest
from app.utilities.scheduling.resource_selection import (
    ensure_party_size_allowed,
    min_notice_seconds,
    seating_resources,
)
from app.utilities.scheduling.zoned_time import (
    microseconds_to_seconds,
    parse_local_date,
)


class CheckAvailabilityUseCase(UseCaseContract[AvailabilityQuery, AvailabilityResult]):
    """
    Free slots (or stays) on a local date of the business (model tool
    check_availability and the cabinet).

    Time-slot resources: the slot must fit an opening range (weekly hours
    with holidays and special hours applied), start after the minimum
    notice, and have a free unit for the slot and its buffer. Night
    resources: no night of the stay may be a closed date, and a unit must
    be free for the whole stay. Resources must seat the party; parties
    above the profile maximum are refused.

    A named service (an id or a name in any script) books its own length
    and buffer with its performers only, and a named resource ("Nino",
    "ნინო") must perform it. A stay of a priced room type carries its quote
    (each night at its season's rate). Without a service the result lists
    the bookable services with their ids.

    With a requested time, up to five slots nearest to it are returned;
    otherwise the first ten. For each time the best-fitting resource is
    offered. Real queries count real bookings; sandbox queries count all.

    The full-day view (`full_day`, staff picking a time in the cabinet)
    lists every free slot of the date for every resource that seats the
    party, by time, then best fit, and every free stay, with the cabinet's
    rules: from now on (no minimum notice), no online party-size limit, and
    a length staff may change.

    Places held for waiting customers count as taken (except for the
    customer a place is held for); a query that finds nothing says whether
    the business keeps a waitlist the customer could join. Times the
    resources' linked calendars made busy (walk-ins in Google Calendar,
    Airbnb reservations, a booking system's bookings) take every unit;
    sources the sync job has not read for two periods are read again
    first, within 2 s.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        resource_repo: ResourceRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
        booking_repo: BookingRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        growth: GrowthBookingsFacilitatorContract,
        busy_times_repo: CalendarBusyTimesRepoContract,
        busy_time_sync: BusyTimeSyncFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._growth: GrowthBookingsFacilitatorContract = growth
        self._busy_times_repo: CalendarBusyTimesRepoContract = busy_times_repo
        self._busy_time_sync: BusyTimeSyncFacilitatorContract = busy_time_sync
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
        )
        self._booking_repo: BookingRepoContract = booking_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AvailabilityQuery) -> AvailabilityResult:
        self._busy_time_sync.refresh_stale(
            input_data.business_id, ON_DEMAND_READ_SECONDS
        )
        inputs: SchedulingInputs = load_scheduling_inputs(
            self._business_repo,
            self._business_profile_repo,
            self._resource_repo,
            self._schedule_exception_repo,
            input_data.business_id,
            self._busy_times_repo,
        )
        if input_data.party_size is not None and not input_data.full_day:
            ensure_party_size_allowed(input_data.party_size, inputs.rules)

        local_date: date = parse_local_date(input_data.date)
        items: list[KnowledgeItemDocument] = self._knowledge_item_repo.list_by_business(
            input_data.business_id
        )
        choice: OfferChoice = choose_offer(
            inputs,
            items,
            OfferRequest(
                service_reference=input_data.service_reference,
                service_item_id=input_data.service_item_id,
                resource_reference=input_data.resource_reference,
                resource_id=input_data.resource_id,
                resource_kind=input_data.resource_kind,
                duration_minutes=input_data.duration_minutes,
                is_duration_override_allowed=input_data.full_day,
            ),
        )
        now: Microseconds = self._wall_clock.now_unix()
        now_seconds: int = microseconds_to_seconds(int(now))
        request = PlacementRequest(
            local_date=local_date,
            minute_of_day=None,
            duration_minutes=choice.duration_minutes,
            nights=None if input_data.nights is None else int(input_data.nights),
            zone=inputs.zone,
            business_hours=inputs.business_hours,
            exceptions=inputs.exceptions,
            bookings=bookings_not_over_on(
                self._booking_repo,
                input_data.business_id,
                local_date,
                inputs.zone,
                HeldPlaces(self._growth, now, input_data.contact_id),
            ),
            rules=inputs.rules,
            stay_times=inputs.stay_times,
            earliest_start=(
                now_seconds
                if input_data.full_day
                else now_seconds + min_notice_seconds(inputs.rules)
            ),
            include_sandbox=input_data.is_sandbox,
            excluded_booking_id=input_data.excluded_booking_id,
            sandbox_conversation_id=input_data.conversation_id,
            buffer_minutes=choice.buffer_minutes,
            blocked_times=inputs.blocked_times,
        )
        candidates: list[ResourceDocument] = seating_resources(
            choice.candidates, input_data.party_size
        )
        currency: CurrencyCode = inputs.business.currency_code
        slots: list[AvailableSlot] = (
            all_time_slots(candidates, request, input_data)
            if input_data.full_day
            else nearest_time_slots(candidates, request, input_data)
        ) + free_stays(
            candidates,
            request,
            input_data,
            StayPricing(offer=choice.offer, items=items, currency_code=currency),
        )
        is_open: bool = is_open_for(local_date, choice.candidates, inputs)
        return AvailabilityResult(
            timezone=inputs.business.timezone,
            is_open_on_date=is_open,
            slots=slots,
            service=(
                None
                if choice.offer is None
                else build_offer_view(choice.offer, inputs.resources, items, currency)
            ),
            services=(
                list_offer_views(inputs.resources, items, currency)
                if choice.offer is None
                else []
            ),
            is_waitlist_open=(
                not slots
                and is_open
                and not input_data.full_day
                and self._growth.is_waitlist_open(input_data.business_id)
            ),
        )
