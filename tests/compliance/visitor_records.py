"""Seed a visitor with conversations, calls, bookings, leads and handoffs."""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus, LeadType
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import LlmTurnRole, MessageAuthor
from app.schemas.constants.handoffs import HandoffReason
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import HandoffDocument
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
from app.schemas.typings.contacts.strings import ContactName
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
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from tests.users.accounts_testbed import AccountsTestbed

BUSINESS_PHONE_NUMBER: E164PhoneNumber = E164PhoneNumber("+995322123456")


@dataclass(frozen=True)
class SeededVisitor:
    contact: ContactDocument
    chat_conversation: ConversationDocument
    phone_conversation: ConversationDocument
    messages: list[MessageDocument]
    llm_turns: list[LlmTurnDocument]
    conversation_call: CallDocument
    phone_matched_call: CallDocument
    booking: BookingDocument
    lead: LeadDocument
    handoff: HandoffDocument


def seed_visitor(
    testbed: AccountsTestbed,
    business: BusinessDocument,
    name: str,
    phone_number: str,
    telegram_chat_id: str,
    language: str,
) -> SeededVisitor:
    """Store a complete visitor history in `business` and return it."""

    now: Microseconds = testbed.clock.now_microseconds()
    contact = ContactDocument(
        business_id=business.id,
        name=ContactName(name),
        phone_number=E164PhoneNumber(phone_number),
        language=LanguageTag(language),
        channel_identities=[
            ChannelIdentity(
                channel=ChannelKind.TELEGRAM,
                channel_user_id=ChannelUserId(telegram_chat_id),
            )
        ],
    )
    testbed.contact_repo.save(contact)
    chat_conversation = build_conversation(
        business,
        contact,
        ChannelKind.TELEGRAM,
        telegram_chat_id,
        now,
    )
    phone_conversation = build_conversation(
        business,
        contact,
        ChannelKind.PHONE,
        phone_number,
        now,
    )
    messages: list[MessageDocument] = []
    llm_turns: list[LlmTurnDocument] = []
    for conversation, texts in (
        (chat_conversation, [f"Hi, I am {name}", "Table for 4 at 20:00?"]),
        (phone_conversation, ["Call transcript summary"]),
    ):
        testbed.conversation_repo.save(conversation)
        for sequence_number, text in enumerate(texts):
            message = MessageDocument(
                conversation_id=conversation.id,
                business_id=business.id,
                direction=MessageDirection.INBOUND,
                author=MessageAuthor.CUSTOMER,
                text=MessageText(text),
                language=LanguageTag(language),
            )
            turn = LlmTurnDocument(
                conversation_id=conversation.id,
                sequence_number=LlmTurnSequenceNumber(sequence_number),
                role=LlmTurnRole.USER,
                payload=LlmProviderPayload(f'{{"role":"user","content":"{text}"}}'),
            )
            testbed.message_repo.save(message)
            testbed.llm_turn_repo.append(turn)
            messages.append(message)
            llm_turns.append(turn)

    conversation_call = CallDocument(
        business_id=business.id,
        conversation_id=phone_conversation.id,
        from_phone_number=E164PhoneNumber(phone_number),
        to_phone_number=BUSINESS_PHONE_NUMBER,
        started_at=now,
        recording_path=RecordingStoragePath(f"recordings/{contact.id}/1.mp3"),
        transcript=CallTranscriptText(f"{name}: I would like to book a table."),
        provider_call_id=ProviderCallId(f"call-{contact.id}-1"),
    )
    phone_matched_call = CallDocument(
        business_id=business.id,
        from_phone_number=E164PhoneNumber(phone_number),
        to_phone_number=BUSINESS_PHONE_NUMBER,
        started_at=now,
        recording_path=RecordingStoragePath(f"recordings/{contact.id}/2.mp3"),
        transcript=CallTranscriptText(f"{name}: Do you have parking?"),
        provider_call_id=ProviderCallId(f"call-{contact.id}-2"),
    )
    testbed.call_repo.save(conversation_call)
    testbed.call_repo.save(phone_matched_call)
    booking = BookingDocument(
        business_id=business.id,
        resource_id=ResourceId(),
        contact_id=contact.id,
        conversation_id=chat_conversation.id,
        starts_at=BookingStartsAtUnixSeconds(1_790_100_000),
        ends_at=BookingEndsAtUnixSeconds(1_790_107_200),
        party_size=PartySize(4),
        status=BookingStatus.CONFIRMED,
        source_channel=ChannelKind.TELEGRAM,
        notes=BookingNote(f"{name} needs a high chair"),
    )
    lead = LeadDocument(
        business_id=business.id,
        contact_id=contact.id,
        conversation_id=chat_conversation.id,
        lead_type=LeadType.BANQUET,
        details=LeadDetails(f"Wedding of {name}, 40 guests"),
        party_size=PartySize(40),
        budget=LeadBudgetText("3000 ₾"),
        source_channel=ChannelKind.TELEGRAM,
    )
    handoff = HandoffDocument(
        business_id=business.id,
        conversation_id=chat_conversation.id,
        contact_id=contact.id,
        reason=HandoffReason.COMPLAINT,
        summary=HandoffSummary(f"{name} complains about the bill"),
    )
    testbed.booking_repo.save(booking)
    testbed.lead_repo.save(lead)
    testbed.handoff_repo.save(handoff)
    return SeededVisitor(
        contact=contact,
        chat_conversation=chat_conversation,
        phone_conversation=phone_conversation,
        messages=messages,
        llm_turns=llm_turns,
        conversation_call=conversation_call,
        phone_matched_call=phone_matched_call,
        booking=booking,
        lead=lead,
        handoff=handoff,
    )


def build_conversation(
    business: BusinessDocument,
    contact: ContactDocument,
    channel: ChannelKind,
    channel_user_id: str,
    now: Microseconds,
) -> ConversationDocument:
    return ConversationDocument(
        business_id=business.id,
        contact_id=contact.id,
        assistant_version_id=AssistantVersionId(),
        channel=channel,
        channel_user_id=ChannelUserId(channel_user_id),
        language=contact.language,
        last_message_at=now,
    )
