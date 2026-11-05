"""
How an erased visitor's conversation is marked: it keeps its row (business
records stay) but loses its channel identity, which becomes this prefix and
the conversation's own id. Writers that must never bring personal data back
after an erasure (the customer memory's summaries) check it.
"""

from app.schemas.domain.conversations import ConversationDocument

ERASED_CHANNEL_USER_ID_PREFIX: str = "erased-"


def is_erased_conversation(conversation: ConversationDocument) -> bool:
    """The visitor of the conversation had their data erased."""

    return str(conversation.channel_user_id).startswith(ERASED_CHANNEL_USER_ID_PREFIX)
