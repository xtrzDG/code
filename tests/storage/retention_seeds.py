"""
A customer's conversation and everything that hangs on it, all at one
moment: two messages (one with a stored photo), the model transcript, a
team note, a call with an archived recording, a lead, a booking whose
visit ended then, a handoff and a missed call.
"""

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus, LeadType
from app.schemas.constants.calls import (
    MissedCallReason,
    MissedCallSource,
    TextBackStatus,
)
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import LlmTurnRole, MessageAuthor
from app.schemas.constants.handoffs import HandoffReason
from app.schemas.constants.media import AttachmentKind
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.conversations import (
    CallDocument,
    CallSummary,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.message_media import MessageMediaDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.media import MediaLocation, StoredMediaFile
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.bookings.strings import (
    BookingNote,
    LeadBudgetText,
    LeadDetails,
)
from app.schemas.typings.calls.constrained_strings import CallSummaryText
from app.schemas.typings.calls.prefixed_id import MissedCallId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.constrained_integers import (
    LlmTurnSequenceNumber,
)
from app.schemas.typings.conversations.strings import (
    CallTranscriptText,
    ChannelUserId,
    LlmProviderPayload,
    MessageText,
    ProviderCallId,
    RecordingStoragePath,
)
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.inbox.constrained_strings import ConversationNoteText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.media.constrained_integers import MediaByteCount
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.prefixed_id import MessageMediaId
from app.schemas.typings.media.strings import MediaStoragePath
from app.schemas.typings.users.prefixed_id import UserId

if TYPE_CHECKING:
    from tests.storage.retention_world import RetentionWorld

PHONE: str = "+995555123456"
MICROSECONDS_PER_SECOND: int = 1_000_000


@dataclass(frozen=True)
class SeededHistory:
    conversation: ConversationDocument
    messages: list[MessageDocument]
    call: CallDocument
    lead: LeadDocument
    booking: BookingDocument
    handoff: HandoffDocument
    media: MessageMediaDocument
    missed_call: MissedCallDocument


def seed_history(
    world: RetentionWorld, business: BusinessDocument, at: Microseconds
) -> SeededHistory:
    contact_id = ContactId()
    conversation = ConversationDocument(
        business_id=business.id,
        contact_id=contact_id,
        assistant_version_id=AssistantVersionId(),
        channel=ChannelKind.WHATSAPP,
        channel_user_id=ChannelUserId(PHONE.removeprefix("+")),
        last_message_at=at,
        created_at=at,
        updated_at=at,
    )
    world.conversations.save(conversation)
    messages = [
        MessageDocument(
            conversation_id=conversation.id,
            business_id=business.id,
            direction=direction,
            author=author,
            text=MessageText(text),
            language=LanguageTag("en"),
            created_at=at,
            updated_at=at,
        )
        for direction, author, text in (
            (MessageDirection.INBOUND, MessageAuthor.CUSTOMER, f"I am Nino, {PHONE}"),
            (MessageDirection.OUTBOUND, MessageAuthor.ASSISTANT, "Booked for 4."),
        )
    ]
    for message in messages:
        world.messages.save(message)

    for sequence_number in range(3):
        world.turns.append(
            LlmTurnDocument(
                conversation_id=conversation.id,
                sequence_number=LlmTurnSequenceNumber(sequence_number),
                role=LlmTurnRole.USER,
                payload=LlmProviderPayload('{"role":"user","content":"Nino"}'),
                created_at=at,
                updated_at=at,
            )
        )

    world.notes.add(
        ConversationNoteDocument(
            business_id=business.id,
            conversation_id=conversation.id,
            author_user_id=UserId(),
            text=ConversationNoteText("Nino is allergic to nuts"),
            created_at=at,
            updated_at=at,
        )
    )
    call = CallDocument(
        business_id=business.id,
        conversation_id=conversation.id,
        from_phone_number=E164PhoneNumber(PHONE),
        to_phone_number=E164PhoneNumber("+995322123456"),
        started_at=at,
        recording_path=RecordingStoragePath(f"archive/{conversation.id}.mp3"),
        transcript=CallTranscriptText("Nino: a table for four, please."),
        provider_call_id=ProviderCallId(f"conv_{conversation.id}"),
        summaries=[
            CallSummary(language=LanguageTag("en"), text=CallSummaryText("Nino booked"))
        ],
        created_at=at,
        updated_at=at,
    )
    world.calls.save(call)
    lead = LeadDocument(
        business_id=business.id,
        contact_id=contact_id,
        conversation_id=conversation.id,
        lead_type=LeadType.BANQUET,
        details=LeadDetails("Nino's wedding, 40 guests"),
        budget=LeadBudgetText("3000 GEL"),
        source_channel=ChannelKind.WHATSAPP,
        created_at=at,
        updated_at=at,
    )
    world.leads.save(lead)
    visit_end = int(at) // MICROSECONDS_PER_SECOND
    booking = BookingDocument(
        business_id=business.id,
        resource_id=ResourceId(),
        contact_id=contact_id,
        conversation_id=conversation.id,
        starts_at=BookingStartsAtUnixSeconds(visit_end - 7200),
        ends_at=BookingEndsAtUnixSeconds(visit_end),
        party_size=PartySize(4),
        status=BookingStatus.CONFIRMED,
        source_channel=ChannelKind.WHATSAPP,
        notes=BookingNote("Nino needs a high chair"),
        created_at=at,
        updated_at=at,
    )
    world.bookings.save(booking)
    handoff = HandoffDocument(
        business_id=business.id,
        conversation_id=conversation.id,
        contact_id=contact_id,
        reason=HandoffReason.COMPLAINT,
        summary=HandoffSummary("Nino complains about the bill"),
        created_at=at,
        updated_at=at,
    )
    world.handoffs.save(handoff)
    media = MessageMediaDocument(
        id=MessageMediaId(uuid.uuid5(uuid.NAMESPACE_URL, str(uuid.uuid4()))),
        business_id=business.id,
        message_id=messages[0].id,
        kind=AttachmentKind.IMAGE,
        storage_path=MediaStoragePath(f"media/{conversation.id}.jpg"),
        media_type=MessageMediaType("image/jpeg"),
        byte_count=MediaByteCount(2048),
        created_at=at,
        updated_at=at,
    )
    world.media.save(media)
    world.media_storage.store(
        MediaLocation(business_id=business.id, path=media.storage_path),
        StoredMediaFile(content=b"\xff\xd8photo", media_type=media.media_type),
    )
    missed_call = MissedCallDocument(
        id=MissedCallId(uuid.uuid5(uuid.NAMESPACE_URL, str(uuid.uuid4()))),
        business_id=business.id,
        source=MissedCallSource.PBX,
        provider_call_id=ProviderCallId(f"pbx_{conversation.id}"),
        reason=MissedCallReason.NO_ANSWER,
        caller_phone_number=E164PhoneNumber(PHONE),
        called_at=at,
        language=LanguageTag("en"),
        status=TextBackStatus.QUEUED,
        created_at=at,
        updated_at=at,
    )
    world.missed_calls.insert_if_new(missed_call)
    return SeededHistory(
        conversation=conversation,
        messages=messages,
        call=call,
        lead=lead,
        booking=booking,
        handoff=handoff,
        media=media,
        missed_call=missed_call,
    )
