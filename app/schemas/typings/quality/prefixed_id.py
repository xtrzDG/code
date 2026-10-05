"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class ConversationQualityScoreId(BasePrefixedTypedId):
    """
    Identifier of the judge's score of one real conversation. Derived
    (UUID v5) from the conversation, so a conversation is scored once and a
    repeated nightly run finds the score it already stored.
    """

    prefix = "conversation_quality"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
