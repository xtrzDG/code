"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


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
