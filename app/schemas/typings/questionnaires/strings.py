"""Keep abc order."""

from base_typed_string import BaseTypedString


class AnswerText(BaseTypedString):
    """Owner's answer to one questionnaire question."""


class FactLabel(BaseTypedString):
    """Human label of a business fact shown to the language model."""


class FactValue(BaseTypedString):
    """Value of a business fact, e.g. "Mon–Fri 09:00–23:00"."""


class FaqAnswerText(BaseTypedString):
    """Owner-approved answer to a frequent customer question."""


class FaqQuestionText(BaseTypedString):
    """Frequent customer question as the owner wrote it."""


class OfferingDescription(BaseTypedString):
    """Short description of a menu item, room type, or service."""


class OfferingName(BaseTypedString):
    """Name of a menu item, room type, or service with a price."""


class ResourceName(BaseTypedString):
    """Name of a bookable resource, e.g. "Table by the window", "VR room 2"."""


# Keep abc order for all non example types, if possible.
