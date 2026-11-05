"""
pass^k: a launch-critical scenario is played several times and passes only
when every play passed, since a model that books correctly one time in two
is not ready for customers.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AutotestOutcome
from app.schemas.domain.assistants import AutotestScenarioResult
from app.schemas.typings.assistants.constrained_integers import (
    AutotestPassedSampleCount,
    AutotestSampleCount,
)
from app.schemas.typings.billing.constrained_integers import CostMicroUsd


def merge_sample_results(
    plays: Sequence[AutotestScenarioResult],
    planned: AutotestSampleCount,
) -> AutotestScenarioResult:
    """
    One result for a scenario's plays (at least one; the plays stop at the
    first that did not pass): that play (its outcome, transcript, scores
    and notes), else the last one; every play's cost; how many were played
    and passed. A scenario planned for a single play keeps its result as
    it is.
    """

    if int(planned) == 1:
        return plays[0]

    reported: AutotestScenarioResult = next(
        (play for play in plays if play.outcome is not AutotestOutcome.PASSED),
        plays[-1],
    )
    return reported.model_copy(
        update={
            "cost_micro_usd": CostMicroUsd(
                sum(int(play.cost_micro_usd) for play in plays)
            ),
            "sample_count": AutotestSampleCount(len(plays)),
            "passed_sample_count": AutotestPassedSampleCount(
                sum(1 for play in plays if play.outcome is AutotestOutcome.PASSED)
            ),
        }
    )
