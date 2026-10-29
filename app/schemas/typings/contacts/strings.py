"""Keep abc order."""

from base_typed_string import BaseTypedString


class ContactName(BaseTypedString):
    """Name a customer gave or a channel reported."""


class FoldedContactName(BaseTypedString):
    """
    A customer's name as the search compares it: without accents, case
    folded, single spaces ("José  Núñez" -> "jose nunez"), in any script.
    The exact-name lookup of the customer list matches it.
    """


class MaskedPhoneNumber(BaseTypedString):
    """
    A customer's phone with the middle digits hidden for staff the owner
    did not allow to see phone numbers ("+995 ••• ••• •34").
    """


# Keep abc order for all non example types, if possible.
