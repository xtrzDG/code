"""Keep abc order."""

from base_typed_string import BaseTypedString


class QuickReplyFilledText(BaseTypedString):
    """
    A saved reply as staff send it in one conversation: the template of the
    chosen language with its variables filled in; a variable without a
    value (no booking yet) stays in braces for staff to complete.

    Example:
        text = QuickReplyFilledText("Hello Nino, see you at Oct 3, 2026, 7:30 PM!")
    """


# Keep abc order for all non example types, if possible.
