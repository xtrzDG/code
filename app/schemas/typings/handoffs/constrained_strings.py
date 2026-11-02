"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class AssistantHandoffSummary(BaseConstrainedTypedString):
    """
    The short retelling the assistant passes to handoff_to_human for staff:
    1 to 1000 characters, no control characters except line breaks and
    tabs.

    Example:
        summary = AssistantHandoffSummary("The guest asks for a table by the window.")
    """

    min_length = 1
    max_length = 1000
    pattern = r"^[^\x00-\x08\x0b\x0c\x0e-\x1f\x7f]*\Z"


class ManagerTelegramUsername(BaseConstrainedTypedString):
    """
    The public Telegram username of a staff member who linked their chat
    to the platform bot, without "@"; the cabinet shows it instead of the
    numeric chat id.

    Example:
        username = ManagerTelegramUsername("nino_k")
    """

    min_length = 4
    max_length = 32
    pattern = r"^[A-Za-z][A-Za-z0-9_]{3,31}$"


# Keep abc order for all non example types, if possible.
