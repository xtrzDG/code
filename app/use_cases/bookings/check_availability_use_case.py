from datetime import date

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    ResourceRepoContract,
    ScheduleExceptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingUnit
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import (
    AvailabilityQuery,
    AvailabilityResult,
    AvailableSlot,
)
from app.schemas.typings.bookings.booleans import IsOpenOnDate
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    NightCount,
)
from app.use_cases.bookings.booking_support import (
    SchedulingInputs,
    load_scheduling_inputs,
)
from app.utilities.scheduling.availability import is_resource_open_on
from app.utilities.scheduling.booking_placement import (
    DEFAULT_NIGHT_COUNT,
    free_stay,
    free_time_slots,
)
from app.utilities.scheduling.opening_hours import business_day_ranges, is_open_on_date
from app.utilities.scheduling.placement import Placement
from app.utilities.scheduling.placement_request import PlacementRequest
from app.utilities.scheduling.resource_selection import (
    ensure_party_size_allowed,
    min_notice_seconds,
    resolve_duration_minutes,
    seating_resources,
    select_resources,
)
from app.utilities.scheduling.slots import nearest_minutes
from app.utilities.scheduling.zoned_time import (
    microseconds_to_seconds,
    parse_local_date,
    parse_time_of_day,
    to_time_of_day,
)

NEAREST_SLOT_LIMIT: int = 5
FIRST_SLOT_LIMIT: int = 10
STAY_OPTION_LIMIT: int = 10


class CheckAvailabilityUseCase(UseCaseContract[AvailabilityQuery, AvailabilityResult]):
    """
    Free slots (or stays) on a local date of the business (model tool
    check_availability and the cabinet).

    Time-slot resources: the slot must fit an opening range (weekly hours
    with holidays and special hours applied), start after the minimum
    notice, and have a free unit. Night resources: no night of the stay may
    be a closed date, and a unit must be free for the whole stay. Resources
    must seat the party; parties above the profile maximum are refused.

    With a requested time, up to five slots nearest to it are returned;
    otherwise the first ten. For each time the best-fitting resource is
    offered. Real queries count real bookings; sandbox queries count all.

    The full-day view (`full_day`, staff picking a time in the cabinet)
    lists every free slot of the date for every resource that seats the
    party, by time, then best fit, and every free stay, with the cabinet's
    rules: from now on (no minimum notice) and no online party-size limit.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        resource_repo: ResourceRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
        booking_repo: BookingRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
        )
        self._booking_repo: BookingRepoContract = booking_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AvailabilityQuery) -> AvailabilityResult:
        inputs: SchedulingInputs = load_scheduling_inputs(
            self._business_repo,
            self._business_profile_repo,
            self._resource_repo,
            self._schedule_exception_repo,
            input_data.business_id,
        )
        if input_data.party_size is not None and not input_data.full_day:
            ensure_party_size_allowed(input_data.party_size, inputs.rules)

        local_date: date = parse_local_date(input_data.date)
        matching: list[ResourceDocument] = select_resources(
            inputs.resources,
            input_data.resource_id,
            input_data.resource_kind,
            inputs.rules,
        )
        now_seconds: int = microseconds_to_seconds(int(self._wall_clock.now_unix()))
        request = PlacementRequest(
            local_date=local_date,
            minute_of_day=None,
            duration_minutes=input_data.duration_minutes,
            nights=None if input_data.nights is None else int(input_data.nights),
            zone=inputs.zone,
            business_hours=inputs.business_hours,
            exceptions=inputs.exceptions,
            bookings=self._booking_repo.list_by_business(input_data.business_id),
            rules=inputs.rules,
            stay_times=inputs.stay_times,
            earliest_start=(
                now_seconds
                if input_data.full_day
                else now_seconds + min_notice_seconds(inputs.rules)
            ),
            include_sandbox=input_data.is_sandbox,
        )
        candidates: list[ResourceDocument] = seating_resources(
            matching, input_data.party_size
        )
        slots: list[AvailableSlot] = (
            self._all_time_slots(candidates, request, input_data)
            if input_data.full_day
            else self._time_slots(candidates, request, input_data)
        ) + self._stays(candidates, request, input_data)
        return AvailabilityResult(
            timezone=inputs.business.timezone,
            is_open_on_date=self._is_open(local_date, matching, inputs),
            slots=slots,
        )

    def _time_slots(
        self,
        candidates: list[ResourceDocument],
        request: PlacementRequest,
        query: AvailabilityQuery,
    ) -> list[AvailableSlot]:
        best_by_minute: dict[int, AvailableSlot] = {}
        for resource in candidates:
            if resource.booking_unit is not BookingUnit.TIME_SLOT:
                continue

            duration: int = resolve_duration_minutes(
                request.duration_minutes, resource, request.rules
            )
            for slot in free_time_slots(resource, request):
                best_by_minute.setdefault(
                    slot.minute_of_day,
                    AvailableSlot(
                        resource_id=resource.id,
                        resource_name=resource.name,
                        booking_unit=BookingUnit.TIME_SLOT,
                        date=query.date,
                        time=to_time_of_day(slot.minute_of_day),
                        duration_minutes=BookingDurationMinutes(duration),
                    ),
                )

        minutes: list[int] = sorted(best_by_minute)
        if query.time is not None:
            minutes = nearest_minutes(
                minutes, parse_time_of_day(query.time), NEAREST_SLOT_LIMIT
            )
        else:
            minutes = minutes[:FIRST_SLOT_LIMIT]

        return [best_by_minute[minute] for minute in minutes]

    def _all_time_slots(
        self,
        candidates: list[ResourceDocument],
        request: PlacementRequest,
        query: AvailabilityQuery,
    ) -> list[AvailableSlot]:
        """Every free slot of every resource, by time, best fit first."""

        slots: list[tuple[int, int, AvailableSlot]] = []
        for rank, resource in enumerate(candidates):
            if resource.booking_unit is not BookingUnit.TIME_SLOT:
                continue

            duration: BookingDurationMinutes = BookingDurationMinutes(
                resolve_duration_minutes(
                    request.duration_minutes, resource, request.rules
                )
            )
            slots.extend(
                (
                    slot.minute_of_day,
                    rank,
                    AvailableSlot(
                        resource_id=resource.id,
                        resource_name=resource.name,
                        booking_unit=BookingUnit.TIME_SLOT,
                        date=query.date,
                        time=to_time_of_day(slot.minute_of_day),
                        duration_minutes=duration,
                    ),
                )
                for slot in free_time_slots(resource, request)
            )

        return [slot for _, _, slot in sorted(slots, key=lambda item: item[:2])]

    def _stays(
        self,
        candidates: list[ResourceDocument],
        request: PlacementRequest,
        query: AvailabilityQuery,
    ) -> list[AvailableSlot]:
        nights: int = request.nights or DEFAULT_NIGHT_COUNT
        stays: list[AvailableSlot] = []
        for resource in candidates:
            if resource.booking_unit is not BookingUnit.NIGHT:
                continue

            placement: Placement | None = free_stay(resource, request)
            if placement is None:
                continue

            stays.append(
                AvailableSlot(
                    resource_id=resource.id,
                    resource_name=resource.name,
                    booking_unit=BookingUnit.NIGHT,
                    date=query.date,
                    time=to_time_of_day(request.stay_times.check_in_minute),
                    nights=NightCount(nights),
                )
            )

        return stays if query.full_day else stays[:STAY_OPTION_LIMIT]

    def _is_open(
        self,
        local_date: date,
        matching: list[ResourceDocument],
        inputs: SchedulingInputs,
    ) -> IsOpenOnDate:
        if not matching:
            return is_open_on_date(
                local_date,
                business_day_ranges(inputs.business_hours, inputs.exceptions),
            )

        return any(
            is_resource_open_on(
                local_date, resource, inputs.business_hours, inputs.exceptions
            )
            for resource in matching
        )
