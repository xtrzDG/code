"""The places of a calendar and the bookings drawn on them."""

from collections.abc import Sequence
from zoneinfo import ZoneInfo

from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.booking_grid import BookingGridPlace
from app.schemas.dto.bookings import BookingView
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.utilities.scheduling.booking_views import build_booking_view


def shown_places(
    resources: Sequence[ResourceDocument], bookings: Sequence[BookingDocument]
) -> list[ResourceDocument]:
    """Active places in their own order; an inactive one while it still has bookings."""

    booked: set[ResourceId] = {booking.resource_id for booking in bookings}
    return [
        resource
        for resource in resources
        if resource.is_active or resource.id in booked
    ]


def by_place(
    bookings: Sequence[BookingDocument],
) -> dict[ResourceId, list[BookingDocument]]:
    grouped: dict[ResourceId, list[BookingDocument]] = {}
    for booking in bookings:
        grouped.setdefault(booking.resource_id, []).append(booking)

    return grouped


def grid_place(resource: ResourceDocument) -> BookingGridPlace:
    return BookingGridPlace(
        id=resource.id,
        name=resource.name,
        kind=resource.kind,
        booking_unit=resource.booking_unit,
        capacity=resource.capacity,
        unit_count=resource.unit_count,
        slot_minutes=resource.slot_minutes,
        is_active=resource.is_active,
        serves_item_ids=list(resource.serves_item_ids),
    )


def booking_views(
    contact_repo: ContactRepoContract,
    knowledge_item_repo: KnowledgeItemRepoContract,
    business_id: BusinessId,
    timezone: TimezoneName,
    zone: ZoneInfo,
    resources: Sequence[ResourceDocument],
    bookings: Sequence[BookingDocument],
) -> list[BookingView]:
    """The bookings as the list shows them (contacts and services in one read each)."""

    contacts: dict[ContactId, ContactDocument] = contact_repo.get_many(
        business_id, [booking.contact_id for booking in bookings]
    )
    services: dict[KnowledgeItemId, KnowledgeItemDocument] = (
        knowledge_item_repo.get_many(
            business_id,
            [
                booking.service_item_id
                for booking in bookings
                if booking.service_item_id is not None
            ],
        )
    )
    places: dict[ResourceId, ResourceDocument] = {
        resource.id: resource for resource in resources
    }
    return [
        build_booking_view(
            booking,
            timezone,
            zone,
            places.get(booking.resource_id),
            contacts.get(booking.contact_id),
            (
                None
                if booking.service_item_id is None
                else services.get(booking.service_item_id)
            ),
        )
        for booking in bookings
    ]
