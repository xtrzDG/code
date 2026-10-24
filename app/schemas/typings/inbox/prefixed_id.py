"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class ConversationNoteId(BasePrefixedTypedId):
    """Random identifier of an internal note on a conversation."""

    prefix = "conversation_note"


class InboxSettingsId(BasePrefixedTypedId):
    """
    Identifier of the team inbox settings of a business.

    Derived (UUID v5) from the business: one settings document per business.
    """

    prefix = "inbox_settings"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class QuickReplyId(BasePrefixedTypedId):
    """Random identifier of one saved reply of a business."""

    prefix = "quick_reply"


class QuickReplyLibraryId(BasePrefixedTypedId):
    """
    Identifier of the saved replies of a business, kept together.

    Derived (UUID v5) from the business: one library per business.
    """

    prefix = "quick_reply_library"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
