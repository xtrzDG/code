"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class OwnerTestChatSessionKey(BaseConstrainedTypedString):
    """
    Key that separates parallel owner test chats of one user, e.g. "tab-2".

    Example:
        key = OwnerTestChatSessionKey("tab-2")
    """

    min_length = 1
    max_length = 64
    pattern = r"^[A-Za-z0-9][A-Za-z0-9_\-]*$"


# Keep abc order for all non example types, if possible.
