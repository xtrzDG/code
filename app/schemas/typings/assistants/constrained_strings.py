"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class AutotestScenarioKey(BaseConstrainedTypedString):
    """
    Stable key of one autotest scenario, e.g. "booking__ka".

    Example:
        key = AutotestScenarioKey("price_question__en")
    """

    min_length = 3
    max_length = 96
    pattern = r"^[a-z][a-z0-9_\-]*$"


class LlmModelId(BaseConstrainedTypedString):
    """
    Language model identifier, e.g. "claude-opus-5-5".

    Example:
        model = LlmModelId("claude-opus-5-5")
    """

    min_length = 3
    max_length = 128
    pattern = r"^[a-z0-9][a-z0-9.\-:@_]*$"


# Keep abc order for all non example types, if possible.
