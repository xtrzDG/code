"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class FactKey(BaseConstrainedTypedString):
    """
    Snake-case key of one business fact, e.g. "opening_hours".

    Example:
        key = FactKey("parking")
    """

    min_length = 2
    max_length = 64
    pattern = r"^[a-z][a-z0-9_]*$"


class QuestionChoiceKey(BaseConstrainedTypedString):
    """Snake-case key of one predefined answer choice."""

    min_length = 1
    max_length = 64
    pattern = r"^[a-z0-9][a-z0-9_]*$"


class QuestionKey(BaseConstrainedTypedString):
    """
    Snake-case key of one questionnaire question.

    Example:
        key = QuestionKey("deposit_policy")
    """

    min_length = 2
    max_length = 64
    pattern = r"^[a-z][a-z0-9_]*$"


# Keep abc order for all non example types, if possible.
