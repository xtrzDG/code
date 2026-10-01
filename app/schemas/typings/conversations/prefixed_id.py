"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class ConversationId(BasePrefixedTypedId):
    """Random identifier of a customer conversation."""

    prefix = "conversation"


class ConversationMessageId(BasePrefixedTypedId):
    """Random identifier of one customer-visible message."""

    prefix = "conversation_message"


class LlmTurnId(BasePrefixedTypedId):
    """Random identifier of one raw language-model transcript turn."""

    prefix = "llm_turn"


# Keep abc order for all non example types, if possible.
