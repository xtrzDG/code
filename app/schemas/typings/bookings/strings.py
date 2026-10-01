"""Keep abc order."""

from base_typed_string import BaseTypedString


class BookingNote(BaseTypedString):
    """Free-form wish attached to a booking ("high chair", "late arrival")."""


class LeadBudgetText(BaseTypedString):
    """Budget exactly as the customer stated it, in any currency or words."""


class LeadDetails(BaseTypedString):
    """What the customer wants from a manager (banquet, group stay, order)."""


# Keep abc order for all non example types, if possible.
