"""Keep abc order."""

from base_typed_float import BaseConstrainedTypedFloat


class VoiceAgentTemperature(BaseConstrainedTypedFloat):
    """
    How freely the voice agent's language model words its answers, from
    0.0 (always the most likely words) to 1.0; low for booking accuracy.
    """

    ge = 0.0
    le = 1.0


class VoiceStability(BaseConstrainedTypedFloat):
    """
    How steady a voice speaks, from 0.0 (lively, varied) to 1.0 (even,
    monotone): the voice platform's `stability`.
    """

    ge = 0.0
    le = 1.0


# Keep abc order for all non example types, if possible.
