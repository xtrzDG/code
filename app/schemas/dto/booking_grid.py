"""
The bookings calendar of the cabinet: one window of local days with every
place, its opening hours and how full it is each day, and the bookings
that fall in the window (GET /v1/businesses/{id}/bookings/grid).
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.dto.bookings import BookingView
from app.schemas.typings.bookings.booleans import (
    AreGridBookingsIncluded,
    IsBookingGridTruncated,
    IsOpenOnDate,
    IsResourceActive,
    IsSandboxIncluded,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookedUnitCount,
    BookedUnitMinutes,
    BookingGridDayCount,
    BookingSearchBoundSeconds,
    GridBookingCount,
    OpenUnitCount,
    OpenUnitMinutes,
    ResourceCapacity,
    ResourceUnitCount,
    SlotDurationMinutes,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.schemas.typings.users.prefixed_id import UserId


class BookingGridQuery(ImmutableDTO):
    """
    The calendar from the local date `date_from` for `days` days. Test
    bookings only with `include_sandbox`; `include_bookings` False leaves
    the bookings out and keeps the counts (the week's heatmap). Shows
    customers' names, so a call is audited as a view by the staff member.
    """

    business_id: BusinessId
    actor_id: UserId
    client_ip_address: ClientIpAddress | None = None
    date_from: LocalDate
    days: BookingGridDayCount
    include_sandbox: IsSandboxIncluded = False
    include_bookings: AreGridBookingsIncluded = True


class BookingWindow(ImmutableDTO):
    """
    One read of a calendar window: bookings that start from `starts_from`
    and before `starts_before` and end after `ends_after` (and by
    `ends_by` when given); cancelled ones never, test ones only with
    `include_sandbox`. Both ends bounded, so a read never walks a
    business's whole history.
    """

    starts_from: BookingSearchBoundSeconds
    starts_before: BookingSearchBoundSeconds
    ends_after: BookingSearchBoundSeconds
    ends_by: BookingSearchBoundSeconds | None = None
    include_sandbox: IsSandboxIncluded = False


class GridOpenRange(ImmutableDTO):
    """An opening range within one local day (minutes from its midnight)."""

    opens_at: OpeningMinuteOfDay
    closes_at: ClosingMinuteOfDay


class BookingGridPlace(ImmutableDTO):
    """
    A place of the calendar (a column of the day, a row of the week and of
    the nights): how it is booked and how many it holds. An inactive place
    shows only while it still has bookings in the window.
    """

    id: ResourceId
    name: ResourceName
    kind: ResourceKind
    booking_unit: BookingUnit
    capacity: ResourceCapacity
    unit_count: ResourceUnitCount
    slot_minutes: SlotDurationMinutes | None = None
    is_active: IsResourceActive
    serves_item_ids: list[KnowledgeItemId] = Field(
        default_factory=list[KnowledgeItemId]
    )


class BookingGridPlaceDay(ImmutableDTO):
    """
    One place on one day. A place booked by time slots has its opening
    ranges and its load in unit-minutes (`open_unit_minutes` it could
    fill, `booked_unit_minutes` its bookings fill within its hours); a
    place booked by the night has rooms (`open_units` for sale that
    night, `booked_units` taken). `booking_count` counts the bookings on
    the day (the stays over the night).
    """

    resource_id: ResourceId
    is_open: IsOpenOnDate
    open_ranges: list[GridOpenRange] = Field(default_factory=list[GridOpenRange])
    booking_count: GridBookingCount
    open_unit_minutes: OpenUnitMinutes | None = None
    booked_unit_minutes: BookedUnitMinutes | None = None
    open_units: OpenUnitCount | None = None
    booked_units: BookedUnitCount | None = None


class BookingGridDay(ImmutableDTO):
    """A local day: the business's own opening ranges and every place on it."""

    date: LocalDate
    business_ranges: list[GridOpenRange] = Field(default_factory=list[GridOpenRange])
    places: list[BookingGridPlaceDay] = Field(default_factory=list[BookingGridPlaceDay])


class BookingGrid(ImmutableDTO):
    """
    The calendar window `date_from`..`date_to` (inclusive local dates) in
    the business time zone. `is_truncated`: the window holds more bookings
    than one calendar reads, so the counts and the bookings are incomplete.
    """

    date_from: LocalDate
    date_to: LocalDate
    timezone: TimezoneName
    places: list[BookingGridPlace] = Field(default_factory=list[BookingGridPlace])
    days: list[BookingGridDay] = Field(default_factory=list[BookingGridDay])
    bookings: list[BookingView] = Field(default_factory=list[BookingView])
    is_truncated: IsBookingGridTruncated = False
