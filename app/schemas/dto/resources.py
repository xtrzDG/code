"""Bookable resources, their schedules and schedule exceptions (holidays).

Times are minutes of the local day in the business time zone; dates are
business-local calendar dates. Storage stays in UTC elsewhere.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.businesses import Weekday
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.typings.bookings.booleans import IsClosedAllDay, IsResourceActive
from app.schemas.typings.bookings.constrained_integers import (
    ResourceCapacity,
    ResourceUnitCount,
    SlotDurationMinutes,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import ResourceId, ScheduleExceptionId
from app.schemas.typings.bookings.strings import ResourceName, ScheduleExceptionNote
from app.schemas.typings.businesses.prefixed_id import BusinessId


class ResourceInput(ImmutableDTO):
    """
    A new bookable resource (table, room type, master, arena, bay, car).

    `kind` and `booking_unit` default to the niche of the business. An empty
    `schedule` means the resource follows the business opening hours.
    """

    kind: ResourceKind | None = None
    name: ResourceName
    capacity: ResourceCapacity
    unit_count: ResourceUnitCount = ResourceUnitCount(1)
    booking_unit: BookingUnit | None = None
    slot_minutes: SlotDurationMinutes | None = None
    schedule: list[OpeningInterval] = Field(default_factory=list[OpeningInterval])
    is_active: IsResourceActive = True


class ResourcePatch(ImmutableDTO):
    """
    Partial update of a resource.

    Only fields present in the request change; an explicit null clears
    `slot_minutes`, and an empty `schedule` returns to the business hours.
    Resources are switched off with `is_active` instead of being deleted, so
    past bookings keep their resource.
    """

    kind: ResourceKind | None = None
    name: ResourceName | None = None
    capacity: ResourceCapacity | None = None
    unit_count: ResourceUnitCount | None = None
    booking_unit: BookingUnit | None = None
    slot_minutes: SlotDurationMinutes | None = None
    schedule: list[OpeningInterval] | None = None
    is_active: IsResourceActive | None = None


class CreateResourceCommand(ImmutableDTO):
    """Add a resource to a business."""

    business_id: BusinessId
    resource: ResourceInput


class UpdateResourceCommand(ImmutableDTO):
    """Change a resource of a business."""

    business_id: BusinessId
    resource_id: ResourceId
    patch: ResourcePatch


class ResourceListQuery(ImmutableDTO):
    """List resources; `is_active` None lists active and inactive ones."""

    business_id: BusinessId
    is_active: IsResourceActive | None = None


class ResourceView(ImmutableDTO):
    """A resource as the owner sees it."""

    id: ResourceId
    business_id: BusinessId
    kind: ResourceKind
    name: ResourceName
    capacity: ResourceCapacity
    unit_count: ResourceUnitCount
    booking_unit: BookingUnit
    slot_minutes: SlotDurationMinutes | None = None
    schedule: list[OpeningInterval] = Field(default_factory=list[OpeningInterval])
    is_active: IsResourceActive
    created_at: Microseconds
    updated_at: Microseconds


class ResourceList(ImmutableDTO):
    """Resources of one business ordered by kind and name."""

    items: list[ResourceView] = Field(default_factory=list[ResourceView])


class ScheduleExceptionInput(ImmutableDTO):
    """
    A holiday, closed day or special-hours day.

    `resource_id` None applies to the whole business. A closed day has no
    special hours; an open day needs special hours on the weekday of `date`.
    """

    resource_id: ResourceId | None = None
    date: LocalDate
    is_closed_all_day: IsClosedAllDay = True
    special_hours: list[OpeningInterval] = Field(default_factory=list[OpeningInterval])
    note: ScheduleExceptionNote | None = None


class CreateScheduleExceptionCommand(ImmutableDTO):
    """Add a schedule exception to a business."""

    business_id: BusinessId
    exception: ScheduleExceptionInput


class ScheduleExceptionListQuery(ImmutableDTO):
    """
    List schedule exceptions.

    With `resource_id`, lists what applies to that resource: its own
    exceptions and the business-wide ones. `from_date` hides earlier days.
    """

    business_id: BusinessId
    resource_id: ResourceId | None = None
    from_date: LocalDate | None = None


class DeleteScheduleExceptionCommand(ImmutableDTO):
    """Delete a schedule exception of a business."""

    business_id: BusinessId
    exception_id: ScheduleExceptionId


class ScheduleExceptionView(ImmutableDTO):
    """A schedule exception with the weekday of its date."""

    id: ScheduleExceptionId
    business_id: BusinessId
    resource_id: ResourceId | None = None
    date: LocalDate
    weekday: Weekday
    is_closed_all_day: IsClosedAllDay
    special_hours: list[OpeningInterval] = Field(default_factory=list[OpeningInterval])
    note: ScheduleExceptionNote | None = None


class ScheduleExceptionList(ImmutableDTO):
    """Schedule exceptions ordered by date."""

    items: list[ScheduleExceptionView] = Field(
        default_factory=list[ScheduleExceptionView]
    )


class ScheduleExceptionDeletion(ImmutableDTO):
    """Identifier of the deleted schedule exception."""

    id: ScheduleExceptionId
