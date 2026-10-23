"""Keep abc order."""

from base_typed_string import BaseTypedString


class VoiceCheckBrief(BaseTypedString):
    """
    What the simulated caller of a voice check is told: who it calls, the
    language it speaks and what it wants (the platform's simulation
    scenario).
    """


class VoiceCheckCondition(BaseTypedString):
    """
    What a simulated call must show to pass, judged by the voice platform's
    evaluator ("The agent made the booking the caller asked for ...").
    """


class VoiceCheckRationale(BaseTypedString):
    """The voice platform's reason for the result of one simulated call."""


# Keep abc order for all non example types, if possible.
