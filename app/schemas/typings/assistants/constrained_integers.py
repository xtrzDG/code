"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class AssistantVersionNumber(BaseConstrainedTypedInt):
    """Sequential number of an assistant version inside one business (1, 2, ...)."""

    ge = 1


class AutotestCaseLimit(BaseConstrainedTypedInt):
    """How many owner checks one business may keep (each runs in every apply)."""

    ge = 1
    le = 200


class AutotestPassedSampleCount(BaseConstrainedTypedInt):
    """How many plays of one sampled autotest scenario passed (0 to 5)."""

    ge = 0
    le = 5


class AutotestSampleCount(BaseConstrainedTypedInt):
    """
    How many times one autotest scenario is played (pass^k): a launch-
    critical scenario passes only when every one of its plays passed
    (AUTOTEST_CRITICAL_SAMPLES).
    """

    ge = 1
    le = 5


class AutotestScenarioCount(BaseConstrainedTypedInt):
    """Number of scenarios in one autotest run (all, passed, failed)."""

    ge = 0


class AutotestTurnLimit(BaseConstrainedTypedInt):
    """Maximum number of customer turns in one autotest conversation."""

    ge = 1
    le = 20


class JudgeScore(BaseConstrainedTypedInt):
    """Judge score of one criterion, 1 (bad) to 5 (perfect)."""

    ge = 1
    le = 5


class LlmCallRetryLimit(BaseConstrainedTypedInt):
    """How many times one language-model call is retried after a failure."""

    ge = 0
    le = 5


class LlmCallTimeoutSeconds(BaseConstrainedTypedInt):
    """
    How long one language-model call of a customer chat may take before it
    is given up (LLM_CALL_TIMEOUT_SECONDS), in seconds.
    """

    ge = 1
    le = 600


class LlmConcurrencyLimit(BaseConstrainedTypedInt):
    """
    How many language-model calls one process makes at the same time
    (LLM_MAX_CONCURRENCY); further calls wait for a free place.
    """

    ge = 1
    le = 512


class LlmMaxOutputTokens(BaseConstrainedTypedInt):
    """Upper bound of output tokens for one language-model request."""

    ge = 1
    le = 128000


class LlmPricePerMillionTokensMicroUsd(BaseConstrainedTypedInt):
    """
    Provider list price of one million tokens, in millionths of a US dollar.

    Example:
        input_price = LlmPricePerMillionTokensMicroUsd(250_000)  # $0.25
    """

    ge = 0


class LlmToolRoundLimit(BaseConstrainedTypedInt):
    """Maximum number of tool-use rounds inside one assistant reply."""

    ge = 1
    le = 20


class PriceQuestionScenarioLimit(BaseConstrainedTypedInt):
    """Maximum number of per-item price autotest scenarios in one run."""

    ge = 0
    le = 100


class ScriptedLlmLatencyMilliseconds(BaseConstrainedTypedInt):
    """
    How long the scripted model (`LLM_PROVIDER=scripted`) waits before it
    answers (SCRIPTED_LLM_LATENCY_MS), in milliseconds: load tests give it
    the latency of a real provider. 0 answers at once.
    """

    ge = 0
    le = 60_000


# Keep abc order for all non example types, if possible.
