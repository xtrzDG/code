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


class CustomerTag(BaseConstrainedTypedString):
    """
    A label the team puts on customers ("regular", "allergy", "wholesale"):
    1 to 32 characters, no line breaks or other control characters, no
    spaces at either end.

    Example:
        tag = CustomerTag("regular")
    """

    min_length = 1
    max_length = 32
    pattern = r"^[^\s\x00-\x1f\x7f](?:[^\x00-\x1f\x7f]{0,30}[^\s\x00-\x1f\x7f])?\Z"


class CustomerTagKey(BaseConstrainedTypedString):
    """
    A tag as tags compare: case-folded ("Regular" and "REGULAR" are the key
    "regular"). Stored next to the tag, so the list and segments filter by
    it in the database. Folding may lengthen a tag ("ß" is "ss"): up to 64
    characters.

    Example:
        key = CustomerTagKey("regular")
    """

    min_length = 1
    max_length = 64
    pattern = r"^[^\s\x00-\x1f\x7f](?:[^\x00-\x1f\x7f]{0,62}[^\s\x00-\x1f\x7f])?\Z"


class SegmentName(BaseConstrainedTypedString):
    """
    The owner's name of a saved group of customers ("Not back in 60 days"):
    1 to 60 characters, no line breaks or other control characters, no
    spaces at either end.
    """

    min_length = 1
    max_length = 60
    pattern = r"^[^\s\x00-\x1f\x7f](?:[^\x00-\x1f\x7f]{0,58}[^\s\x00-\x1f\x7f])?\Z"


# Keep abc order for all non example types, if possible.
