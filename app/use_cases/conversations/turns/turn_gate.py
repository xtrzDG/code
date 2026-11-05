"""
Whether the assistant answers a message: a blocked customer, handoffs, the
injection brake, the hourly limit and the length of a conversation.
"""

from datetime import timedelta

from typed_time_provider import Microseconds

from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversation_engine import TurnGate
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.reply_safety import InjectionSignal
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.conversations.constrained_integers import (
    ContactMessageLimit,
    InjectionFlagLimit,
)
from app.use_cases.conversations.turns.injection_brake import choose_injection_gate
from app.use_cases.shared.turn_time import to_microseconds

CONTACT_LIMIT_WINDOW: timedelta = timedelta(hours=1)
# Customer messages one conversation is answered for. A real conversation
# ends long before; past it the assistant closes politely and stays silent
# until a new conversation starts (24 hours without a message), while the
# team still sees every message in the inbox.
MAX_CONVERSATION_MESSAGES: int = 150


def choose_turn_gate(
    conversation_repo: ConversationRepoContract,
    message_repo: MessageRepoContract,
    contact_message_limit: ContactMessageLimit,
    business: BusinessDocument,
    contact: ContactDocument,
    conversation: ConversationDocument,
    now: Microseconds,
    injection_flag: InjectionSignal | None,
    injection_flag_limit: InjectionFlagLimit,
) -> TurnGate:
    """
    A customer the owner blocked hears nothing (Customers → block). Staff
    own a conversation in HANDOFF (silence in chat, a call-back promise on
    the phone); a contact who keeps trying prompt injection, is past the
    hourly per-contact limit is answered once with a polite stop message;
    one who wrote MAX_CONVERSATION_MESSAGES messages in this conversation
    is told once that the conversation ends here (CONVERSATION_LIMIT_NOTICE);
    then the assistant stays silent.
    """

    if contact.block is not None and not conversation.is_sandbox:
        return TurnGate.BLOCKED_SILENCE

    if conversation.status is ConversationStatus.HANDOFF:
        return (
            TurnGate.STAFF_CALLBACK
            if conversation.channel is ChannelKind.PHONE
            else TurnGate.STAFF_SILENCE
        )

    injection_gate: TurnGate | None = choose_injection_gate(
        conversation_repo,
        message_repo,
        injection_flag_limit,
        business,
        contact,
        injection_flag,
        now,
    )
    if injection_gate is not None:
        return injection_gate

    recent_message_count: int = count_recent_inbound_messages(
        conversation_repo, message_repo, business, contact, now
    )
    conversation_message_count: int = int(
        message_repo.count_by_conversation(
            business.id, conversation.id, MessageDirection.INBOUND
        )
    )
    if (
        recent_message_count > int(contact_message_limit)
        or conversation_message_count > MAX_CONVERSATION_MESSAGES
    ):
        return TurnGate.LIMIT_SILENCE

    if conversation_message_count == MAX_CONVERSATION_MESSAGES:
        return TurnGate.CONVERSATION_LIMIT_NOTICE

    if recent_message_count == int(contact_message_limit):
        return TurnGate.LIMIT_NOTICE

    return TurnGate.ANSWER


def count_recent_inbound_messages(
    conversation_repo: ConversationRepoContract,
    message_repo: MessageRepoContract,
    business: BusinessDocument,
    contact: ContactDocument,
    now: Microseconds,
) -> int:
    """
    Inbound messages of the contact in the last hour, in every channel:
    the contact's conversations with a message in that hour, and an indexed
    count of each one's recent inbound messages.
    """

    window_start = Microseconds(int(now) - to_microseconds(CONTACT_LIMIT_WINDOW))
    recent_message_count: int = 0
    for conversation in conversation_repo.list_by_contact(
        business.id, contact.id, last_message_from=window_start
    ):
        recent_message_count += int(
            message_repo.count_by_conversation(
                business.id,
                conversation.id,
                MessageDirection.INBOUND,
                created_from=window_start,
            )
        )

    return recent_message_count
