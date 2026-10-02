"""Keep abc order."""

from base_typed_string import BaseTypedString


class ApplyAttentionMessage(BaseTypedString):
    """Plain-language reason why applied changes are not live yet."""


class SetupActionLabel(BaseTypedString):
    """Label of the button that takes the owner to the next setup action."""


class SetupStepDescription(BaseTypedString):
    """One sentence on what a setup step asks of the owner."""


class SetupStepTitle(BaseTypedString):
    """Short title of a setup step ("Hours and bookings")."""


# Keep abc order for all non example types, if possible.
