"""Keep abc order."""

from base_typed_string import BaseTypedString


class CancellationPolicyText(BaseTypedString):
    """Cancellation rule as the owner wrote it ("free up to 2 hours before")."""


class FactLabel(BaseTypedString):
    """Human label of a business fact shown to the language model."""


class FactValue(BaseTypedString):
    """Value of a business fact, e.g. "Mon–Fri 09:00–23:00"."""


class ForbiddenRuleText(BaseTypedString):
    """Something the assistant must never do ("no discounts without approval")."""


class HandoffRuleText(BaseTypedString):
    """Owner rule for passing to a human ("banquet over 20 people")."""


class ProfileAnswerText(BaseTypedString):
    """Owner's answer to one niche-specific profile question."""


class ToneText(BaseTypedString):
    """Desired tone of the assistant ("friendly and short")."""


# Keep abc order for all non example types, if possible.
