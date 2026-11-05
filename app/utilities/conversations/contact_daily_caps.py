"""
Per-contact daily caps of what reaches the team: requests (leads) a
customer can make in its conversations and staff alerts of handoffs it can
set off in 24 hours, so an anonymous visitor cannot flood staff with them
(an emergency always alerts; bookings have caps of their own; the
business-wide spend limit still holds).

A record of the last 24 hours belongs to a conversation of the contact with
a message in that time (a lead or a handoff is made while its conversation
is active), so the count reads the contact's recent conversations
(indexed) and their records (indexed); test chats never count.
"""

from collections.abc import Callable, Iterable, Sequence
from datetime import timedelta
from typing import Protocol

from typed_time_provider import Microseconds

from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId

DAILY_CAP_WINDOW: timedelta = timedelta(hours=24)
MAX_LEADS_PER_CONTACT_PER_DAY: int = 5
MAX_HANDOFF_ALERTS_PER_CONTACT_PER_DAY: int = 3


class ContactRecord(Protocol):
    """A lead or a handoff, as the caps read it."""

    @property
    def contact_id(self) -> ContactId: ...

    @property
    def is_sandbox(self) -> IsSandboxConversation: ...

    @property
    def created_at(self) -> Microseconds: ...


def daily_window_start(now: Microseconds) -> Microseconds:
    """The start of the 24 hours before `now`."""

    window: int = int(DAILY_CAP_WINDOW.total_seconds()) * 1_000_000
    return Microseconds(int(now) - window)


def count_made_since[Record: ContactRecord](
    conversations: Iterable[ConversationDocument],
    records_of: Callable[[ConversationId], Sequence[Record]],
    contact_id: ContactId,
    since: Microseconds,
) -> int:
    """The contact's real records made at or after `since`."""

    return sum(
        1
        for conversation in conversations
        for record in records_of(conversation.id)
        if record.contact_id == contact_id
        and not record.is_sandbox
        and int(record.created_at) >= int(since)
    )
