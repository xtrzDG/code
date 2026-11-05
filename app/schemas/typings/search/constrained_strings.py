"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class CabinetSearchText(BaseConstrainedTypedString):
    """
    What someone typed into the cabinet's search (Cmd/Ctrl+K): part of a
    customer's name, digits of a phone, or the id of a customer,
    conversation or booking.

    Example:
        query = CabinetSearchText("Ирина")
    """

    min_length = 1
    max_length = 100


# Keep abc order for all non example types, if possible.
