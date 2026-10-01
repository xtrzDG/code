"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class AssistantVersionNumber(BaseConstrainedTypedInt):
    """Sequential number of an assistant version inside one business (1, 2, ...)."""

    ge = 1


class AutotestTurnLimit(BaseConstrainedTypedInt):
    """Maximum number of customer turns in one autotest conversation."""

    ge = 1
    le = 20


class JudgeScore(BaseConstrainedTypedInt):
    """Judge score of one criterion, 1 (bad) to 5 (perfect)."""

    ge = 1
    le = 5


class LlmMaxOutputTokens(BaseConstrainedTypedInt):
    """Upper bound of output tokens for one language-model request."""

    ge = 1
    le = 128000


class LlmToolRoundLimit(BaseConstrainedTypedInt):
    """Maximum number of tool-use rounds inside one assistant reply."""

    ge = 1
    le = 20


# Keep abc order for all non example types, if possible.
