"""The bookings, leads and handoffs made in one conversation (indexed reads)."""

from dataclasses import dataclass
from zoneinfo import ZoneInfo

from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.knowledge_repositories import ResourceRepoContract
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.operations.handoffs import HandoffListItem
from app.schemas.dto.operations.leads import LeadListItem
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.use_cases.handoffs.handoff_views import build_handoff_list_item
from app.use_cases.leads.lead_views import build_lead_list_item
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.zoned_time import load_time_zone


@dataclass(frozen=True)
class ConversationLinks:
    """What came out of a conversation, ready for its card."""

    bookings: list[BookingView]
    leads: list[LeadListItem]
    handoffs: list[HandoffListItem]


def collect_conversation_links(
    business: BusinessDocument,
    conversation_id: ConversationId,
    contact: ContactDocument | None,
    booking_repo: BookingRepoContract,
    lead_repo: LeadRepoContract,
    handoff_repo: HandoffRepoContract,
    resource_repo: ResourceRepoContract,
    contact_repo: ContactRepoContract,
) -> ConversationLinks:
    """
    Bookings by start time, leads and handoffs newest first, each with its
    contact (usually the conversation's own).
    """

    bookings: list[BookingDocument] = booking_repo.list_by_conversation(
        business.id, conversation_id
    )
    leads: list[LeadDocument] = lead_repo.list_by_conversation(
        business.id, conversation_id
    )
    handoffs: list[HandoffDocument] = handoff_repo.list_by_conversation(
        business.id, conversation_id
    )
    contacts: dict[ContactId, ContactDocument] = (
        {} if contact is None else {contact.id: contact}
    )
    others: list[ContactId] = [
        item.contact_id
        for item in (*bookings, *leads, *handoffs)
        if item.contact_id not in contacts
    ]
    if others:
        contacts.update(contact_repo.get_many(business.id, others))

    resources: dict[ResourceId, ResourceDocument] = (
        {
            resource.id: resource
            for resource in resource_repo.list_by_business(business.id)
        }
        if bookings
        else {}
    )
    zone: ZoneInfo = load_time_zone(business.timezone)
    return ConversationLinks(
        bookings=[
            build_booking_view(
                booking,
                business.timezone,
                zone,
                resources.get(booking.resource_id),
                contacts.get(booking.contact_id),
            )
            for booking in bookings
        ],
        leads=[
            build_lead_list_item(lead, contacts.get(lead.contact_id)) for lead in leads
        ],
        handoffs=[
            build_handoff_list_item(handoff, contacts.get(handoff.contact_id))
            for handoff in handoffs
        ],
    )
