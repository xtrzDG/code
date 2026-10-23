"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class AsrKeyword(BaseConstrainedTypedString):
    """
    A word or short phrase the voice platform's speech recognition listens
    for in a call: the business's name, a master's or a room's name, a dish
    or a service. One line, at most 60 characters.

    Example:
        keyword = AsrKeyword("Khachapuri Adjaruli")
    """

    min_length = 1
    max_length = 60
    pattern = r"^[^\x00-\x1f\x7f]+$"


class VoiceAgentLlmId(BaseConstrainedTypedString):
    """
    The language model the voice platform runs the agent on, by the
    platform's own name ("gemini-2.5-flash", "gpt-4.1-mini").

    Example:
        llm = VoiceAgentLlmId("gemini-2.5-flash")
    """

    min_length = 2
    max_length = 64
    pattern = r"^[a-z0-9][a-z0-9.@_\-]+$"


class VoiceCheckInvocationId(BaseConstrainedTypedString):
    """
    The voice platform's id of one run of voice checks (a test invocation
    of ElevenLabs agent testing), polled until its tests finish.

    Example:
        invocation_id = VoiceCheckInvocationId("ti_0000000000")
    """

    min_length = 1
    max_length = 128
    pattern = r"^[A-Za-z0-9_\-]+$"


class VoiceCheckTestId(BaseConstrainedTypedString):
    """
    The voice platform's id of one simulated test call (an ElevenLabs agent
    test), deleted once its run finished.

    Example:
        test_id = VoiceCheckTestId("test_0000000000")
    """

    min_length = 1
    max_length = 128
    pattern = r"^[A-Za-z0-9_\-]+$"


class VoicePlatformVoiceId(BaseConstrainedTypedString):
    """
    A voice of the voice platform's library (ElevenLabs voice id).

    Example:
        voice_id = VoicePlatformVoiceId("EXAVITQu4vr4xnSDxMaL")
    """

    min_length = 10
    max_length = 40
    pattern = r"^[A-Za-z0-9]+$"


class VoiceTtsModelId(BaseConstrainedTypedString):
    """
    The voice platform's speech model ("eleven_flash_v2_5" for low latency,
    "eleven_v3_conversational" for the widest choice of languages).

    Example:
        model = VoiceTtsModelId("eleven_flash_v2_5")
    """

    min_length = 8
    max_length = 48
    pattern = r"^eleven_[a-z0-9_]+$"


# Keep abc order for all non example types, if possible.
