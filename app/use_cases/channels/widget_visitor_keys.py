"""
A website chat visitor's key expires on the server after idling: what it
held before a gap of `VISITOR_KEY_IDLE_DAYS` without a message is no longer
readable with it. The key is the visitor's only credential (whoever holds
it reads the chat), and it lives in the browser of a shared computer or a
copied link for as long as nobody clears it; an idle key reads nothing at
all, and a key used again after the gap starts afresh, its new
conversation alone readable (and in a conversation staff kept open across
the gap, only what came after it).
"""

from typed_time_provider import Microseconds

from app.schemas.domain.conversations import ConversationDocument, MessageDocument

VISITOR_KEY_IDLE_DAYS: int = 30
MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000
IDLE_LIMIT_MICROSECONDS: int = VISITOR_KEY_IDLE_DAYS * MICROSECONDS_PER_DAY


def readable_conversations(
    conversations: list[ConversationDocument], now: Microseconds
) -> list[ConversationDocument]:
    """
    The visitor's conversations their key may still read, newest first: the
    run of conversations back from now without an idle gap (from one
    conversation's last message to the start of the next newer one, or to
    now for the newest). Empty when the key idled since its last message.
    """

    readable: list[ConversationDocument] = []
    boundary: int = int(now)
    for conversation in sorted(
        conversations, key=lambda item: int(item.last_message_at), reverse=True
    ):
        if boundary - int(conversation.last_message_at) > IDLE_LIMIT_MICROSECONDS:
            break

        readable.append(conversation)
        boundary = min(boundary, int(conversation.created_at))
    return readable


def after_last_idle_gap(messages: list[MessageDocument]) -> list[MessageDocument]:
    """
    Messages in answer order without those before the latest idle gap
    inside them (a conversation staff kept open across the gap).
    """

    start: int = 0
    for index in range(1, len(messages)):
        gap: int = int(messages[index].created_at) - int(messages[index - 1].created_at)
        if gap > IDLE_LIMIT_MICROSECONDS:
            start = index
    return messages[start:]
