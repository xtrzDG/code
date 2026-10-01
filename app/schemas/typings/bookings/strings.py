"""Keep abc order."""

from base_typed_string import BaseTypedString


class BookingNote(BaseTypedString):
    """Free-form wish attached to a booking ("high chair", "late arrival")."""


class LeadBudgetText(BaseTypedString):
    """Budget exactly as the customer stated it, in any currency or words."""


class LeadDetails(BaseTypedString):
    """What the customer wants from a manager (banquet, group stay, order)."""


class ResourceName(BaseTypedString):
    """Name of a bookable resource, e.g. "Table 4", "VR arena 2", "Nino"."""


class ScheduleExceptionNote(BaseTypedString):
    """Why a day is closed or has special hours ("Orthodox Christmas")."""


# Keep abc order for all non example types, if possible.
