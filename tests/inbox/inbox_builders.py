"""Customers, conversations and the work they leave, for the inbox tests."""

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus, LeadStatus, LeadType
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.constants.handoffs import HandoffReason, HandoffStatus, HandoffUrgency
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.bookings.strings import LeadDetails
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from tests.inbox.inbox_store import InboxStore

MINUTE: int = 60_000_000


def talk(
    store: InboxStore,
    name: str | None,
    minutes_ago: int,
    text: str = "Hello, is there a table for tonight?",
    channel: ChannelKind = ChannelKind.TELEGRAM,
    language: str | None = "ka",
    is_sandbox: bool = False,
) -> ConversationDocument:
    """A customer who wrote `minutes_ago` minutes before the store's now."""

    at = Microseconds(int(store.now) - minutes_ago * MINUTE)
    user_id = ChannelUserId(f"user-{name}-{minutes_ago}")
    contact = ContactDocument(
        business_id=store.business.id,
        name=None if name is None else ContactName(name),
        phone_number=E164PhoneNumber("+995555123456"),
        channel_identities=[ChannelIdentity(channel=channel, channel_user_id=user_id)],
        created_at=at,
        updated_at=at,
    )
    store.contact_repo.save(contact)
    conversation = ConversationDocument(
        business_id=store.business.id,
        contact_id=contact.id,
        assistant_version_id=AssistantVersionId(),
        channel=channel,
        channel_user_id=user_id,
        language=None if language is None else LanguageTag(language),
        is_sandbox=is_sandbox,
        last_message_at=at,
        created_at=at,
        updated_at=at,
    )
    store.conversation_repo.save(conversation)
    store.message_repo.save(
        MessageDocument(
            conversation_id=conversation.id,
            business_id=store.business.id,
            direction=MessageDirection.INBOUND,
            author=MessageAuthor.CUSTOMER,
            text=MessageText(text),
            created_at=at,
            updated_at=at,
        )
    )
    return conversation


def hand_off(
    store: InboxStore,
    conversation: ConversationDocument,
    urgency: HandoffUrgency = HandoffUrgency.NORMAL,
) -> HandoffDocument:
    """The assistant passed the conversation to a person (still open)."""

    handoff = HandoffDocument(
        business_id=store.business.id,
        conversation_id=conversation.id,
        contact_id=conversation.contact_id,
        reason=HandoffReason.CUSTOMER_REQUEST,
        summary=HandoffSummary("Wants to talk to a person."),
        urgency=urgency,
        status=HandoffStatus.NOTIFIED,
        is_sandbox=conversation.is_sandbox,
        created_at=conversation.last_message_at,
        updated_at=conversation.last_message_at,
    )
    store.handoff_repo.save(handoff)
    conversation.status = ConversationStatus.HANDOFF
    store.conversation_repo.save(conversation)
    return handoff


def request(
    store: InboxStore,
    conversation: ConversationDocument,
    status: LeadStatus = LeadStatus.NEW,
) -> LeadDocument:
    """A request (lead) made in the conversation, its flag kept as the app does."""

    lead = LeadDocument(
        business_id=store.business.id,
        contact_id=conversation.contact_id,
        conversation_id=conversation.id,
        lead_type=LeadType.BANQUET,
        details=LeadDetails("A birthday dinner for 20 people."),
        party_size=PartySize(20),
        source_channel=conversation.channel,
        status=status,
        is_sandbox=conversation.is_sandbox,
        created_at=conversation.last_message_at,
        updated_at=conversation.last_message_at,
    )
    store.lead_repo.save(lead)
    store.conversation_repo.set_open_request(
        store.business.id,
        conversation.id,
        store.inbox_work_repo.has_open_request(store.business.id, conversation.id),
        store.now,
    )
    return lead


def book(
    store: InboxStore,
    conversation: ConversationDocument,
    starts_in_minutes: int,
    status: BookingStatus = BookingStatus.CONFIRMED,
) -> BookingDocument:
    """A booking made in the conversation, starting after the store's now."""

    start: int = int(store.now) // 1_000_000 + starts_in_minutes * 60
    booking = BookingDocument(
        business_id=store.business.id,
        resource_id=ResourceId(),
        contact_id=conversation.contact_id,
        conversation_id=conversation.id,
        starts_at=BookingStartsAtUnixSeconds(start),
        ends_at=BookingEndsAtUnixSeconds(start + 7200),
        party_size=PartySize(2),
        status=status,
        source_channel=conversation.channel,
        created_at=store.now,
        updated_at=store.now,
    )
    store.booking_repo.save(booking)
    return booking


def reload(
    store: InboxStore, conversation: ConversationDocument
) -> ConversationDocument:
    stored = store.conversation_repo.get(store.business.id, conversation.id)
    assert stored is not None
    return stored
