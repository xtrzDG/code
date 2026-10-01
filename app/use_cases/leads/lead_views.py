"""Leads rendered for the model and the cabinet."""

from app.schemas.domain.bookings import LeadDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.bookings import LeadView
from app.schemas.dto.operations import LeadListItem


def build_lead_view(lead: LeadDocument) -> LeadView:
    return LeadView(
        id=lead.id,
        business_id=lead.business_id,
        contact_id=lead.contact_id,
        lead_type=lead.lead_type,
        details=lead.details,
        requested_date=lead.requested_date,
        party_size=lead.party_size,
        budget=lead.budget,
        source_channel=lead.source_channel,
        status=lead.status,
        is_sandbox=lead.is_sandbox,
    )


def build_lead_list_item(
    lead: LeadDocument,
    contact: ContactDocument | None,
) -> LeadListItem:
    return LeadListItem(
        id=lead.id,
        business_id=lead.business_id,
        contact_id=lead.contact_id,
        contact_name=None if contact is None else contact.name,
        contact_phone_number=None if contact is None else contact.phone_number,
        conversation_id=lead.conversation_id,
        lead_type=lead.lead_type,
        details=lead.details,
        requested_date=lead.requested_date,
        party_size=lead.party_size,
        budget=lead.budget,
        source_channel=lead.source_channel,
        status=lead.status,
        is_sandbox=lead.is_sandbox,
        created_at=lead.created_at,
    )
