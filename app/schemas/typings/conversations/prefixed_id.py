"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class CallId(BasePrefixedTypedId):
    """Random identifier of a phone call record."""

    prefix = "call"


class ConversationId(BasePrefixedTypedId):
    """Random identifier of a customer conversation."""

    prefix = "conversation"


class LlmTurnId(BasePrefixedTypedId):
    """Random identifier of one raw language-model transcript turn."""

    prefix = "llm_turn"


class MessageId(BasePrefixedTypedId):
    """Random identifier of one stored message."""

    prefix = "message"


# Keep abc order for all non example types, if possible.
