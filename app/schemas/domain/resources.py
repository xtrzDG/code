from base_pydantic_schemas import BaseDocument, SchemaVersion
from pydantic import Field

from app.schemas.constants.bookings import BookingUnit, ResourceKind
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
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId


class ResourceDocument(BaseDocument):
    """
    Something bookable (concept tables `resources` and `schedules`).

    Empty `schedule` means the resource follows the business hours. A
    master, a doctor or a bay performs the services of `serves_item_ids`;
    a room is one of the room type `room_type_item_id` (an item of kind
    ROOM_TYPE with its nightly rates). Neither set: the resource takes any
    booking of its kind.
    """

    # 2: `serves_item_ids` and `room_type_item_id` (optional).
    schema_version: SchemaVersion = SchemaVersion("2")
    id: ResourceId = Field(default_factory=ResourceId)
    business_id: BusinessId
    kind: ResourceKind
    name: ResourceName
    capacity: ResourceCapacity
    unit_count: ResourceUnitCount = ResourceUnitCount(1)
    booking_unit: BookingUnit = BookingUnit.TIME_SLOT
    slot_minutes: SlotDurationMinutes | None = None
    schedule: list[OpeningInterval] = Field(default_factory=list[OpeningInterval])
    is_active: IsResourceActive = True
    serves_item_ids: list[KnowledgeItemId] = Field(
        default_factory=list[KnowledgeItemId]
    )
    room_type_item_id: KnowledgeItemId | None = None


class ScheduleExceptionDocument(BaseDocument):
    """
    Holiday or special-hours day (concept `schedule_exceptions`).

    Applies to one resource, or to the whole business when resource_id is null.
    """

    id: ScheduleExceptionId = Field(default_factory=ScheduleExceptionId)
    business_id: BusinessId
    resource_id: ResourceId | None = None
    date: LocalDate
    is_closed_all_day: IsClosedAllDay = True
    special_hours: list[OpeningInterval] = Field(default_factory=list[OpeningInterval])
    note: ScheduleExceptionNote | None = None
