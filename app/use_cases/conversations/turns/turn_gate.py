"""Whether the assistant answers a message: handoffs and the hourly limit."""

from datetime import timedelta

from typed_time_provider import Microseconds

from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversation_engine import TurnGate
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.conversations.constrained_integers import (
    ContactMessageLimit,
)
from app.use_cases.conversations.turns.turn_time import to_microseconds

CONTACT_LIMIT_WINDOW: timedelta = timedelta(hours=1)


def choose_turn_gate(
    conversation_repo: ConversationRepoContract,
    message_repo: MessageRepoContract,
    contact_message_limit: ContactMessageLimit,
    business: BusinessDocument,
    contact: ContactDocument,
    conversation: ConversationDocument,
    now: Microseconds,
) -> TurnGate:
    """
    Staff own a conversation in HANDOFF (silence in chat, a call-back
    promise on the phone); past the hourly per-contact limit the assistant
    answers once with a stop message, then stays silent.
    """

    if conversation.status is ConversationStatus.HANDOFF:
        return (
            TurnGate.STAFF_CALLBACK
            if conversation.channel is ChannelKind.PHONE
            else TurnGate.STAFF_SILENCE
        )

    recent_message_count: int = count_recent_inbound_messages(
        conversation_repo, message_repo, business, contact, now
    )
    if recent_message_count == int(contact_message_limit):
        return TurnGate.LIMIT_NOTICE

    if recent_message_count > int(contact_message_limit):
        return TurnGate.LIMIT_SILENCE

    return TurnGate.ANSWER


def count_recent_inbound_messages(
    conversation_repo: ConversationRepoContract,
    message_repo: MessageRepoContract,
    business: BusinessDocument,
    contact: ContactDocument,
    now: Microseconds,
) -> int:
    """Inbound messages of the contact in the last hour, in every channel."""

    window_start: int = int(now) - to_microseconds(CONTACT_LIMIT_WINDOW)
    recent_message_count: int = 0
    for conversation in conversation_repo.list_by_business(business.id):
        if conversation.contact_id != contact.id:
            continue

        if int(conversation.last_message_at) < window_start:
            continue

        for message in message_repo.list_by_conversation(business.id, conversation.id):
            if (
                message.direction is MessageDirection.INBOUND
                and int(message.created_at) >= window_start
            ):
                recent_message_count += 1

    return recent_message_count
