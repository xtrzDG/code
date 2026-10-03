"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class ConversationNoteText(BaseConstrainedTypedString):
    """
    An internal note of the team on a conversation: only owners and staff
    read it, it is never sent to the customer or the language model. At
    least one visible character.

    Example:
        note = ConversationNoteText("Called back, she prefers Saturday.")
    """

    min_length = 1
    max_length = 4000
    pattern = r"\S"


class QuickReplyShortcut(BaseConstrainedTypedString):
    """
    The word staff type after "/" to pick a saved reply: letters of any
    script, digits, "_" and "-", unique within a business.

    Example:
        shortcut = QuickReplyShortcut("hours")
    """

    min_length = 1
    max_length = 32
    pattern = r"^[\w-]+$"


class QuickReplyTemplateText(BaseConstrainedTypedString):
    """
    The text of a saved reply in one language, with variables in braces
    ({name}, {booking_time}, {business_name}) filled in for each
    conversation. At least one visible character.

    Example:
        text = QuickReplyTemplateText("Hello {name}, see you at {booking_time}!")
    """

    min_length = 1
    max_length = 2000
    pattern = r"\S"


class QuickReplyTitle(BaseConstrainedTypedString):
    """
    The name of a saved reply in the picker. At least one visible character.

    Example:
        title = QuickReplyTitle("Opening hours")
    """

    min_length = 1
    max_length = 80
    pattern = r"\S"


# Keep abc order for all non example types, if possible.
