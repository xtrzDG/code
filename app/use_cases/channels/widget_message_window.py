"""
Which messages a widget poll needs, and positions in them (pure functions).

A poll answers from the visitor's messages in (created_at, id) order: the
assistant's and staff's after the widget's cursor, and the latest message
as the next cursor. Nothing before the cursor matters then, so a poll
first reads only where the newest few messages stand (newest first by
created_at, `MessagePosition`) and uses them when they reach back past the
cursor, reading in full only the messages after it; only a cursor older
than them (a long backlog), an unknown one or none reads the whole chat.
The order and the cursor tests work on positions and messages alike.
"""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit


class PlacedMessage(Protocol):
    """A message or its position: its id and creation time."""

    @property
    def id(self) -> MessageId: ...

    @property
    def created_at(self) -> Microseconds: ...


def message_order(message: PlacedMessage) -> tuple[int, str]:
    """The order a poll answers in: by creation time, ties by id."""

    return (int(message.created_at), str(message.id))


def covers_from_cursor(
    newest: Sequence[PlacedMessage],
    after: MessageId,
    window_size: KeysetReadLimit,
) -> bool:
    """
    Whether `newest` (the newest `window_size` messages, newest first by
    created_at) holds the cursor and every message created at or after
    it, so that the messages after the cursor and the latest one are the
    same as in the whole chat. True when the window is not full (it is the
    whole chat) or reaches back to messages created before the cursor's
    time (any tie with the cursor is then inside it too).
    """

    cursor: PlacedMessage | None = next(
        (message for message in newest if message.id == after), None
    )
    if cursor is None:
        return False

    if len(newest) < int(window_size):
        return True

    oldest_created_at: int = min(int(message.created_at) for message in newest)
    return oldest_created_at < int(cursor.created_at)


def find_position_after(
    messages: Sequence[PlacedMessage],
    after: MessageId | None,
) -> int | None:
    """Index of the first message after `after`; None when it is unknown."""

    if after is None:
        return None

    for index, message in enumerate(messages):
        if message.id == after:
            return index + 1

    return None


def find_latest_visitor_message_id(
    messages: list[MessageDocument],
) -> MessageId | None:
    """The visitor's latest own message: the answers after it are new."""

    for message in reversed(messages):
        if message.author is MessageAuthor.CUSTOMER:
            return message.id

    return None
