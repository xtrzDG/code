"""
The brake on prompt-injection attempts: a contact whose messages keep
looking like injection is answered with the polite limit notice once and
then not at all, until a day passes since those messages.
"""

from datetime import timedelta

from typed_time_provider import Microseconds

from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.schemas.constants.conversation_engine import TurnGate
from app.schemas.constants.reply_safety import InjectionSignal
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.conversations.constrained_integers import (
    InjectionFlagLimit,
)
from app.use_cases.shared.turn_time import to_microseconds

INJECTION_FLAG_WINDOW: timedelta = timedelta(days=1)


def choose_injection_gate(
    conversation_repo: ConversationRepoContract,
    message_repo: MessageRepoContract,
    injection_flag_limit: InjectionFlagLimit,
    business: BusinessDocument,
    contact: ContactDocument,
    injection_flag: InjectionSignal | None,
    now: Microseconds,
) -> TurnGate | None:
    """
    LIMIT_SILENCE when the contact's flagged messages of the last day
    already reached the limit; LIMIT_NOTICE for the flagged message that
    reaches it; None while the contact is below it.
    """

    earlier_flags: int = count_recent_injection_flags(
        conversation_repo, message_repo, business, contact, now
    )
    limit: int = int(injection_flag_limit)
    if earlier_flags >= limit:
        return TurnGate.LIMIT_SILENCE

    if injection_flag is not None and earlier_flags + 1 >= limit:
        return TurnGate.LIMIT_NOTICE

    return None


def count_recent_injection_flags(
    conversation_repo: ConversationRepoContract,
    message_repo: MessageRepoContract,
    business: BusinessDocument,
    contact: ContactDocument,
    now: Microseconds,
) -> int:
    """Flagged messages of the contact in the last day, in every channel."""

    window_start = Microseconds(int(now) - to_microseconds(INJECTION_FLAG_WINDOW))
    return sum(
        int(
            message_repo.count_injection_flags(
                business.id, conversation.id, created_from=window_start
            )
        )
        for conversation in conversation_repo.list_by_contact(
            business.id, contact.id, last_message_from=window_start
        )
    )
