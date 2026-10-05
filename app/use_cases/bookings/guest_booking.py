"""
A booking as its guest sees it, with what the confirmation and the manage
page tell about it: the business and its profile, whether it is a time
slot or a stay, and the booked service's title.
"""

from dataclasses import dataclass

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.schemas.constants.bookings import BookingUnit
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.strings import KnowledgeTitle


@dataclass(frozen=True)
class GuestBooking:
    """One booking with its business, profile, resource, unit and service."""

    business: BusinessDocument
    profile: BusinessProfileDocument | None
    booking: BookingDocument
    resource: ResourceDocument | None
    booking_unit: BookingUnit
    service_title: KnowledgeTitle | None


@dataclass(frozen=True)
class GuestBookingReader:
    """Reads a booking with what its guest is told about it."""

    business_repo: BusinessRepoContract
    business_profile_repo: BusinessProfileRepoContract
    booking_repo: BookingRepoContract
    resource_repo: ResourceRepoContract
    knowledge_item_repo: KnowledgeItemRepoContract

    def read(
        self,
        business_id: BusinessId,
        booking_id: BookingId,
    ) -> GuestBooking | None:
        """None when the business or the booking is gone."""

        business: BusinessDocument | None = self.business_repo.get(business_id)
        booking: BookingDocument | None = self.booking_repo.get(business_id, booking_id)
        if business is None or booking is None:
            return None

        resource: ResourceDocument | None = self.resource_repo.get(
            business_id, booking.resource_id
        )
        service: KnowledgeItemDocument | None = (
            None
            if booking.service_item_id is None
            else self.knowledge_item_repo.get(business_id, booking.service_item_id)
        )
        return GuestBooking(
            business=business,
            profile=self.business_profile_repo.get_by_business(business_id),
            booking=booking,
            resource=resource,
            booking_unit=(
                BookingUnit.TIME_SLOT if resource is None else resource.booking_unit
            ),
            service_title=None if service is None else service.title,
        )
