"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class ContactSearchText(BaseConstrainedTypedString):
    """
    What the owner typed to find a customer: part of a name, digits of a
    phone number, or a contact id.

    Example:
        search = ContactSearchText("599 12")
    """

    min_length = 1
    max_length = 100


# Keep abc order for all non example types, if possible.
