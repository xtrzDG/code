"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class VoiceCheckWaitSeconds(BaseConstrainedTypedInt):
    """
    How long the voice checks of one autotest run may take at the voice
    platform before the ones still running are given up (errored).
    """

    ge = 30
    le = 1800


class VoiceTurnTimeoutSeconds(BaseConstrainedTypedInt):
    """
    How long the voice agent waits for a silent caller before it speaks
    again (asks whether they are still there): the platform's turn timeout.
    """

    ge = 1
    le = 30


# Keep abc order for all non example types, if possible.
