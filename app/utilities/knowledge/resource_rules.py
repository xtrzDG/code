"""Rules for bookable resources.

Defaults come from the niche (a restaurant books tables by time slots, a
hotel books rooms by nights).
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.resources import (
    ResourceInput,
    ResourcePatch,
    ResourceView,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import SlotDurationMinutes
from app.schemas.typings.bookings.strings import ResourceName
from app.utilities.knowledge.opening_hours import validate_opening_intervals
from app.utilities.knowledge.search_text import fold_words

MAX_RESOURCE_NAME_LENGTH: int = 120
REQUIRED_RESOURCE_PATCH_FIELDS: tuple[str, ...] = (
    "kind",
    "name",
    "capacity",
    "unit_count",
    "booking_unit",
    "schedule",
    "is_active",
)


def build_resource(
    business: BusinessDocument,
    template: NicheTemplate,
    resource_input: ResourceInput,
    existing_resources: Sequence[ResourceDocument],
    now: Microseconds,
) -> ResourceDocument:
    """A validated new resource with niche defaults for kind and booking unit."""

    kind: ResourceKind = (
        resource_input.kind
        if resource_input.kind is not None
        else template.resource_kind
    )
    booking_unit: BookingUnit = (
        resource_input.booking_unit
        if resource_input.booking_unit is not None
        else template.booking_unit
    )
    return ResourceDocument(
        business_id=business.id,
        kind=kind,
        name=check_resource_name(resource_input.name, existing_resources),
        capacity=resource_input.capacity,
        unit_count=resource_input.unit_count,
        booking_unit=booking_unit,
        slot_minutes=check_slot_minutes(booking_unit, resource_input.slot_minutes),
        schedule=validate_opening_intervals(
            resource_input.schedule,
            subject="Resource schedule",
        ),
        is_active=resource_input.is_active,
        created_at=now,
        updated_at=now,
    )


def patch_resource(
    existing: ResourceDocument,
    patch: ResourcePatch,
    other_resources: Sequence[ResourceDocument],
    now: Microseconds,
) -> ResourceDocument:
    """
    A resource with the fields present in `patch` changed.

    Only `slot_minutes` can be cleared with null; an empty schedule returns
    the resource to the business hours.
    """

    provided: set[str] = patch.model_fields_set
    for required_field in REQUIRED_RESOURCE_PATCH_FIELDS:
        if required_field in provided and getattr(patch, required_field) is None:
            raise ValidationFailedError(f"Field {required_field} cannot be null.")

    booking_unit: BookingUnit = (
        existing.booking_unit if patch.booking_unit is None else patch.booking_unit
    )
    slot_minutes: SlotDurationMinutes | None = (
        patch.slot_minutes if "slot_minutes" in provided else existing.slot_minutes
    )
    if booking_unit is BookingUnit.NIGHT and "slot_minutes" not in provided:
        slot_minutes = None

    return ResourceDocument(
        id=existing.id,
        business_id=existing.business_id,
        kind=existing.kind if patch.kind is None else patch.kind,
        name=(
            existing.name
            if patch.name is None
            else check_resource_name(patch.name, other_resources)
        ),
        capacity=existing.capacity if patch.capacity is None else patch.capacity,
        unit_count=existing.unit_count
        if patch.unit_count is None
        else patch.unit_count,
        booking_unit=booking_unit,
        slot_minutes=check_slot_minutes(booking_unit, slot_minutes),
        schedule=(
            existing.schedule
            if patch.schedule is None
            else validate_opening_intervals(patch.schedule, subject="Resource schedule")
        ),
        is_active=existing.is_active if patch.is_active is None else patch.is_active,
        created_at=existing.created_at,
        updated_at=now,
    )


def check_resource_name(
    name: ResourceName,
    other_resources: Sequence[ResourceDocument],
) -> ResourceName:
    """
    The name as written, if no other resource of the business uses it
    (ignoring case, accents and spacing).
    """

    stripped_length: int = len(name.strip())
    if stripped_length == 0 or stripped_length > MAX_RESOURCE_NAME_LENGTH:
        raise ValidationFailedError(
            f"A resource needs a name of 1 to {MAX_RESOURCE_NAME_LENGTH} characters."
        )

    folded_name: str = fold_words(name)
    for resource in other_resources:
        if fold_words(resource.name) == folded_name:
            raise ConflictError(f"A resource named {name.strip()!r} already exists.")

    return name


def check_slot_minutes(
    booking_unit: BookingUnit,
    slot_minutes: SlotDurationMinutes | None,
) -> SlotDurationMinutes | None:
    """Night resources are booked by nights and have no slot length."""

    if booking_unit is BookingUnit.NIGHT and slot_minutes is not None:
        raise ValidationFailedError(
            "Resources booked by nights have no slot length; leave slot_minutes empty."
        )

    return slot_minutes


def to_resource_view(resource: ResourceDocument) -> ResourceView:
    return ResourceView(
        id=resource.id,
        business_id=resource.business_id,
        kind=resource.kind,
        name=resource.name,
        capacity=resource.capacity,
        unit_count=resource.unit_count,
        booking_unit=resource.booking_unit,
        slot_minutes=resource.slot_minutes,
        schedule=list(resource.schedule),
        is_active=resource.is_active,
        created_at=resource.created_at,
        updated_at=resource.updated_at,
    )


def resource_sort_key(resource: ResourceDocument) -> tuple[str, str, str]:
    return (resource.kind.value, fold_words(resource.name), str(resource.id))
