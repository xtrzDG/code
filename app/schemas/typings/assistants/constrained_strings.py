"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class AutotestCaseQuestion(BaseConstrainedTypedString):
    """
    What the customer asks in an owner check, word for word: the first
    message of its test conversation; at least one visible character.

    Example:
        question = AutotestCaseQuestion("Do you have a vegetarian menu?")
    """

    min_length = 1
    max_length = 500
    pattern = r"\S"


class AutotestExpectedText(BaseConstrainedTypedString):
    """
    A word, number or phrase an owner check expects the assistant's answer
    to contain (or never to contain); matched ignoring case, accents,
    punctuation and spacing.

    Example:
        expected = AutotestExpectedText("18 GEL")
    """

    min_length = 1
    max_length = 200
    pattern = r"\w"


class AutotestScenarioKey(BaseConstrainedTypedString):
    """
    Stable key of one autotest scenario, e.g. "booking__ka".

    Example:
        key = AutotestScenarioKey("price_question__en")
    """

    min_length = 3
    max_length = 96
    pattern = r"^[a-z][a-z0-9_\-]*$"


class GoLiveCheckDetail(BaseConstrainedTypedString):
    """
    One machine value that qualifies a go-live check: a profile gap kind, a
    subscription or version status, the DPA version to accept or the name
    of a missing server setting.

    Example:
        detail = GoLiveCheckDetail("no_opening_hours")
    """

    min_length = 1
    max_length = 120
    pattern = r"^[A-Za-z0-9][A-Za-z0-9_.:/+\-]*$"


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
