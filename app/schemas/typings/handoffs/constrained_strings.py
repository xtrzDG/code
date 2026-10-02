"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


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
