"""
The WhatsApp conversation a text-back opens: the caller's reply lands in
it like any WhatsApp message, and the assistant (and staff) see what was
sent, because the text-back is its first message (written by the business).
"""

from datetime import timedelta

from typed_time_provider import Microseconds

from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.use_cases.shared.contact_activity import record_contact_seen

MICROSECONDS_PER_SECOND: int = 1_000_000
# The window in which a customer message joins an open conversation.
CONVERSATION_WINDOW: timedelta = timedelta(hours=24)


def whatsapp_user_id(caller: E164PhoneNumber) -> ChannelUserId:
    """WhatsApp names a customer by the international digits of their number."""

    return ChannelUserId(str(caller).removeprefix("+"))


def find_caller_contact(
    contact_repo: ContactRepoContract,
    business: BusinessDocument,
    caller: E164PhoneNumber,
) -> ContactDocument | None:
    """
    The customer behind a calling number: the contact whose phone a call
    or a booking proved, else the one who writes from it on WhatsApp, else
    the one who called from it before.
    """

    return (
        contact_repo.find_by_verified_phone_number(business.id, caller)
        or contact_repo.find_by_channel_identity(
            business.id, ChannelKind.WHATSAPP, whatsapp_user_id(caller)
        )
        or contact_repo.find_by_channel_identity(
            business.id, ChannelKind.PHONE, ChannelUserId(str(caller))
        )
    )


def open_text_back_conversation(
    contact_repo: ContactRepoContract,
    conversation_repo: ConversationRepoContract,
    message_repo: MessageRepoContract,
    business: BusinessDocument,
    caller: E164PhoneNumber,
    text: MessageText,
    language: LanguageTag,
    now: Microseconds,
) -> ConversationId | None:
    """
    The caller's WhatsApp conversation with the text-back as its newest
    message: an open one of the last day, else a new one pinned to the live
    version (None while the business has none). The caller is the contact
    whose phone a call proved, or a new one known by phone and WhatsApp.
    """

    if business.published_assistant_version_id is None:
        return None

    user_id: ChannelUserId = whatsapp_user_id(caller)
    contact: ContactDocument = resolve_caller(
        contact_repo, business, caller, user_id, now
    )
    conversation: ConversationDocument = find_whatsapp_conversation(
        conversation_repo, business, contact, now
    ) or ConversationDocument(
        business_id=business.id,
        contact_id=contact.id,
        assistant_version_id=business.published_assistant_version_id,
        channel=ChannelKind.WHATSAPP,
        channel_user_id=user_id,
        language=language,
        last_message_at=now,
        created_at=now,
        updated_at=now,
    )
    conversation.last_message_at = now
    conversation.updated_at = now
    conversation_repo.save(conversation)
    message_repo.save(
        MessageDocument(
            conversation_id=conversation.id,
            business_id=business.id,
            direction=MessageDirection.OUTBOUND,
            author=MessageAuthor.STAFF,
            text=text,
            language=language,
            created_at=now,
            updated_at=now,
        )
    )
    return conversation.id


def resolve_caller(
    contact_repo: ContactRepoContract,
    business: BusinessDocument,
    caller: E164PhoneNumber,
    user_id: ChannelUserId,
    now: Microseconds,
) -> ContactDocument:
    contact: ContactDocument | None = find_caller_contact(
        contact_repo, business, caller
    )
    identity = ChannelIdentity(channel=ChannelKind.WHATSAPP, channel_user_id=user_id)
    if contact is None:
        contact = ContactDocument(
            business_id=business.id,
            phone_number=caller,
            verified_phone_number=caller,
            channel_identities=[
                ChannelIdentity(
                    channel=ChannelKind.PHONE,
                    channel_user_id=ChannelUserId(str(caller)),
                ),
                identity,
            ],
            created_at=now,
            updated_at=now,
        )
        contact_repo.save(contact)
        return contact

    if identity not in contact.channel_identities:
        contact.channel_identities.append(identity)
        contact.updated_at = now
        contact_repo.save(contact)

    # The missed call is the customer's latest activity.
    return record_contact_seen(contact_repo, contact, now)


def find_whatsapp_conversation(
    conversation_repo: ConversationRepoContract,
    business: BusinessDocument,
    contact: ContactDocument,
    now: Microseconds,
) -> ConversationDocument | None:
    window_start = Microseconds(
        int(now) - int(CONVERSATION_WINDOW.total_seconds()) * MICROSECONDS_PER_SECOND
    )
    for conversation in conversation_repo.list_by_contact(
        business.id, contact.id, last_message_from=window_start
    ):
        if (
            conversation.channel is ChannelKind.WHATSAPP
            and not conversation.is_sandbox
            and conversation.status is not ConversationStatus.CLOSED
        ):
            return conversation

    return None
