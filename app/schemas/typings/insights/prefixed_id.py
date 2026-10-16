"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class ConversationTopicsId(BasePrefixedTypedId):
    """
    Identifier of the topics of one business's recent conversations (what
    customers ask about), as the nightly grouping last stored them.

    Derived (UUID v5) from the business, so each business has one topics
    document that every night's grouping replaces.
    """

    prefix = "conversation_topics"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
