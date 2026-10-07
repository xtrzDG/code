"""Keep abc order."""

from base_typed_string import BaseTypedString


class ApplyAttentionMessage(BaseTypedString):
    """Plain-language reason why applied changes are not live yet."""


class PendingChangeSubject(BaseTypedString):
    """
    What a change not live yet is about, in the owner's own words: the
    title of a menu item or question, the name of a table or room, the
    label of a niche question.
    """


class PendingChangeValue(BaseTypedString):
    """A value before or after a change, as the assistant states it ("18.00 GEL")."""


class SetupActionLabel(BaseTypedString):
    """Label of the button that takes the owner to the next setup action."""


class SetupStepDescription(BaseTypedString):
    """One sentence on what a setup step asks of the owner."""


class SetupStepTitle(BaseTypedString):
    """Short title of a setup step ("Hours and bookings")."""


# Keep abc order for all non example types, if possible.
