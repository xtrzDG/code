"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class ConversationSearchText(BaseConstrainedTypedString):
    """
    What staff type to find conversations: part of a customer's name, phone
    digits in any format, or words of a message, in any script.

    Example:
        search = ConversationSearchText("нино 555")
    """

    min_length = 1
    max_length = 200


class OwnerTestChatSessionKey(BaseConstrainedTypedString):
    """
    Key that separates parallel owner test chats of one user, e.g. "tab-2".

    Example:
        key = OwnerTestChatSessionKey("tab-2")
    """

    min_length = 1
    max_length = 64
    pattern = r"^[A-Za-z0-9][A-Za-z0-9_\-]*$"


class StaffReplyText(BaseConstrainedTypedString):
    """
    Text an owner or staff member writes to a customer from the cabinet;
    at least one visible character.

    Example:
        reply = StaffReplyText("Yes, we will keep the table until 20:30.")
    """

    min_length = 1
    max_length = 4000
    pattern = r"\S"


# Keep abc order for all non example types, if possible.
