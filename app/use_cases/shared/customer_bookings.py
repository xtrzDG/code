"""
A customer's own bookings that are not over yet, as the assistant reads
them: the customer memory's upcoming bookings and the list_my_bookings
tool. Read from the bookings not over at `now` (indexed by their end),
never across businesses.
"""

from collections.abc import Collection

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import BookingView
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.zoned_time import load_time_zone


def find_customer_bookings(
    booking_repo: BookingRepoContract,
    resource_repo: ResourceRepoContract,
    knowledge_item_repo: KnowledgeItemRepoContract,
    business: BusinessDocument,
    contact_ids: Collection[ContactId],
    statuses: Collection[BookingStatus],
    is_sandbox: bool,
    now_seconds: int,
) -> list[BookingView]:
    """
    The bookings of these contacts in these statuses and sandbox mode that
    have not ended at `now_seconds`, the soonest first, in the business's
    time zone with their resource and service.
    """

    bookings: list[BookingDocument] = [
        booking
        for booking in booking_repo.list_ending_after(
            business.id, BookingSearchBoundSeconds(now_seconds)
        )
        if booking.contact_id in contact_ids
        and booking.status in statuses
        and booking.is_sandbox == is_sandbox
    ]
    if not bookings:
        return []

    resources: dict[str, ResourceDocument] = {
        str(resource.id): resource
        for resource in resource_repo.list_by_business(business.id)
    }
    service_ids: list[KnowledgeItemId] = [
        booking.service_item_id
        for booking in bookings
        if booking.service_item_id is not None
    ]
    services: dict[KnowledgeItemId, KnowledgeItemDocument] = (
        knowledge_item_repo.get_many(business.id, service_ids) if service_ids else {}
    )
    zone = load_time_zone(business.timezone)
    return [
        build_booking_view(
            booking,
            business.timezone,
            zone,
            resources.get(str(booking.resource_id)),
            None,
            None
            if booking.service_item_id is None
            else services.get(booking.service_item_id),
        )
        for booking in bookings
    ]
