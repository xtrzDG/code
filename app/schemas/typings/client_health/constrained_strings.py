"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class ClientNoteText(BaseConstrainedTypedString):
    """
    What a platform admin wrote down about a client: a call, a promise, a
    deal (never a customer's personal data). Shown to the platform team
    only.

    Example:
        note = ClientNoteText("Owner prefers WhatsApp; call after 18:00")
    """

    min_length = 1
    max_length = 2000
    pattern = r"^\S[\s\S]*$"


class ClientSearchText(BaseConstrainedTypedString):
    """
    What a platform admin typed to find a client: part of the business name
    or of its id.

    Example:
        search = ClientSearchText("napoli")
    """

    min_length = 1
    max_length = 100


# Keep abc order for all non example types, if possible.
