"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class ConversationQualityScoreId(BasePrefixedTypedId):
    """
    Identifier of the judge's score of one real conversation. Derived
    (UUID v5) from the conversation, so a conversation is scored once and a
    repeated nightly run finds the score it already stored.
    """

    prefix = "conversation_quality"


# Keep abc order for all non example types, if possible.
