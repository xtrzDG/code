"""
Bookable offers (services, packages, room types) and the resources that
perform or provide them.

A resource performs an offer when the offer names it
(`performer_resource_ids`), when the resource names the offer
(`serves_item_ids`), or when a room is of that room type
(`room_type_item_id`): the owner may link them from either side. An offer
nobody is linked to falls to the resources that are not linked to any
offer (generalists), else to every resource booked the same way, so a
business that never links anything books as before.
"""

from collections.abc import Sequence

from app.schemas.constants.bookings import BookingUnit
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.typings.knowledge.constrained_integers import BufferMinutes
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId

BOOKABLE_KINDS: frozenset[KnowledgeItemKind] = frozenset(
    {
        KnowledgeItemKind.SERVICE,
        KnowledgeItemKind.PACKAGE,
        KnowledgeItemKind.ROOM_TYPE,
    }
)
# Kinds whose booking blocks a performer for a while after it ends.
BUFFERED_KINDS: frozenset[KnowledgeItemKind] = frozenset(
    {KnowledgeItemKind.SERVICE, KnowledgeItemKind.PACKAGE}
)


def is_bookable_item(item: KnowledgeItemDocument) -> bool:
    return item.is_active and item.kind in BOOKABLE_KINDS


def booking_unit_of_offer(item: KnowledgeItemDocument) -> BookingUnit:
    """Room types are booked by the night, services and packages by time."""

    if item.kind is KnowledgeItemKind.ROOM_TYPE:
        return BookingUnit.NIGHT

    return BookingUnit.TIME_SLOT


def is_linked(item: KnowledgeItemDocument, resource: ResourceDocument) -> bool:
    """Whether the owner linked the resource and the offer (either side)."""

    return (
        resource.id in item.performer_resource_ids
        or item.id in resource.serves_item_ids
        or resource.room_type_item_id == item.id
    )


def linked_item_ids(
    resource: ResourceDocument,
    items: Sequence[KnowledgeItemDocument],
) -> set[KnowledgeItemId]:
    """The offers a resource is linked to, from both sides."""

    return {item.id for item in items if is_linked(item, resource)}


def performers_of(
    item: KnowledgeItemDocument,
    resources: Sequence[ResourceDocument],
    items: Sequence[KnowledgeItemDocument],
) -> list[ResourceDocument]:
    """
    The active resources that perform or provide the offer (see the module):
    the linked ones, else the generalists, else every resource booked the
    offer's way.
    """

    unit: BookingUnit = booking_unit_of_offer(item)
    active: list[ResourceDocument] = [
        resource
        for resource in resources
        if resource.is_active and resource.booking_unit is unit
    ]
    linked: list[ResourceDocument] = [
        resource for resource in active if is_linked(item, resource)
    ]
    if linked or any(is_linked(item, resource) for resource in resources):
        return linked

    bookable_items: list[KnowledgeItemDocument] = [
        other for other in items if other.kind in BOOKABLE_KINDS
    ]
    generalists: list[ResourceDocument] = [
        resource for resource in active if not linked_item_ids(resource, bookable_items)
    ]
    return generalists or active


def bookable_offers(
    items: Sequence[KnowledgeItemDocument],
) -> list[KnowledgeItemDocument]:
    """Active services, packages and room types, by kind and title."""

    kind_order: list[KnowledgeItemKind] = list(KnowledgeItemKind)
    return sorted(
        (item for item in items if is_bookable_item(item)),
        key=lambda item: (
            kind_order.index(item.kind),
            str(item.title).casefold(),
            str(item.id),
        ),
    )


def buffer_of_offer(offer: KnowledgeItemDocument | None) -> BufferMinutes | None:
    """Minutes the performer stays blocked after a booking of the offer."""

    if offer is None or offer.kind not in BUFFERED_KINDS:
        return None

    if offer.buffer_minutes is None or int(offer.buffer_minutes) == 0:
        return None

    return offer.buffer_minutes
