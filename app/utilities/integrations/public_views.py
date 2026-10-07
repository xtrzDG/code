"""
Stored records in their public shape (`app/schemas/dto/public_api`): the
same view for a webhook's data and the public API's answer.
"""

from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.public_api.activity import (
    PublicCall,
    PublicConversation,
    PublicHandoff,
    PublicMessage,
)
from app.schemas.dto.public_api.records import (
    PublicBooking,
    PublicContact,
    PublicContactRef,
    PublicLead,
    PublicMoney,
    PublicResourceRef,
    PublicServiceRef,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.utilities.integrations.public_timestamps import (
    local_timestamp,
    utc_timestamp,
)


def contact_ref(
    contact_id: ContactId, contact: ContactDocument | None
) -> PublicContactRef:
    """The customer a record is about; only the id when it is gone."""

    if contact is None:
        return PublicContactRef(id=contact_id)

    return PublicContactRef(
        id=contact.id,
        name=contact.name,
        phone_number=contact.verified_phone_number or contact.phone_number,
    )


def public_booking(
    business: BusinessDocument,
    booking: BookingDocument,
    contact: ContactDocument | None,
    resource: ResourceDocument | None,
    service: KnowledgeItemDocument | None,
    conversation: ConversationDocument | None,
) -> PublicBooking:
    return PublicBooking(
        id=booking.id,
        status=booking.status,
        starts_at=local_timestamp(int(booking.starts_at), business.timezone),
        ends_at=local_timestamp(int(booking.ends_at), business.timezone),
        timezone=business.timezone,
        party_size=booking.party_size,
        resource=None
        if resource is None
        else PublicResourceRef(id=resource.id, name=resource.name),
        service=None
        if service is None
        else PublicServiceRef(id=service.id, name=service.title),
        value=None
        if booking.value_minor is None or booking.currency_code is None
        else PublicMoney(
            amount_minor=booking.value_minor, currency=booking.currency_code
        ),
        notes=booking.notes,
        contact=contact_ref(booking.contact_id, contact),
        source_channel=booking.source_channel,
        acquisition_source=None
        if conversation is None
        else conversation.acquisition_source,
        conversation_id=booking.conversation_id,
        created_at=utc_timestamp(booking.created_at),
        updated_at=utc_timestamp(booking.updated_at),
    )


def public_lead(
    lead: LeadDocument,
    contact: ContactDocument | None,
    conversation: ConversationDocument | None,
) -> PublicLead:
    return PublicLead(
        id=lead.id,
        status=lead.status,
        type=lead.lead_type,
        details=lead.details,
        requested_date=lead.requested_date,
        party_size=lead.party_size,
        budget=lead.budget,
        contact=contact_ref(lead.contact_id, contact),
        source_channel=lead.source_channel,
        acquisition_source=None
        if conversation is None
        else conversation.acquisition_source,
        conversation_id=lead.conversation_id,
        created_at=utc_timestamp(lead.created_at),
        updated_at=utc_timestamp(lead.updated_at),
    )


def public_contact(contact: ContactDocument) -> PublicContact:
    return PublicContact(
        id=contact.id,
        name=contact.name,
        phone_number=contact.verified_phone_number or contact.phone_number,
        language=contact.language,
        created_at=utc_timestamp(contact.created_at),
        updated_at=utc_timestamp(contact.updated_at),
    )


def public_conversation(
    conversation: ConversationDocument, contact: ContactDocument | None
) -> PublicConversation:
    return PublicConversation(
        id=conversation.id,
        channel=conversation.channel,
        status=conversation.status,
        contact=contact_ref(conversation.contact_id, contact),
        language=conversation.language,
        acquisition_source=conversation.acquisition_source,
        summary=conversation.summary,
        started_at=utc_timestamp(conversation.created_at),
        last_message_at=utc_timestamp(conversation.last_message_at),
    )


def public_message(message: MessageDocument) -> PublicMessage:
    return PublicMessage(
        id=message.id,
        author=message.author,
        text=message.text,
        created_at=utc_timestamp(message.created_at),
    )


def public_handoff(
    handoff: HandoffDocument, contact: ContactDocument | None
) -> PublicHandoff:
    return PublicHandoff(
        id=handoff.id,
        status=handoff.status,
        reason=handoff.reason,
        urgency=handoff.urgency,
        summary=handoff.summary,
        conversation_id=handoff.conversation_id,
        contact=contact_ref(handoff.contact_id, contact),
        created_at=utc_timestamp(handoff.created_at),
        resolved_at=None
        if handoff.resolved_at is None
        else utc_timestamp(handoff.resolved_at),
    )


def public_call(
    call: CallDocument,
    conversation: ConversationDocument | None,
    contact: ContactDocument | None,
) -> PublicCall:
    return PublicCall(
        id=call.id,
        conversation_id=call.conversation_id,
        from_phone_number=call.from_phone_number,
        to_phone_number=call.to_phone_number,
        started_at=utc_timestamp(call.started_at),
        duration_seconds=call.duration_seconds,
        outcome=call.outcome,
        summary=call.summaries[0].text if call.summaries else None,
        contact=None
        if conversation is None
        else contact_ref(conversation.contact_id, contact),
        acquisition_source=None
        if conversation is None
        else conversation.acquisition_source,
    )
