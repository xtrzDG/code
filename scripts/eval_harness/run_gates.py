"""
What makes a run fail (exit code 1 of scripts/run_evals.py): a regression
against the baseline, a stale cassette, a pass rate under the floor, a
hallucination rate over the ceiling, or with --require-pass any failed
scenario. The CI replay gate runs with a floor of 100% and a ceiling of 0
(the scripted references pass and never invent); a live model's floor and
ceiling are the nightly job's inputs.
"""

from dataclasses import dataclass

from scripts.eval_harness.baselines import BaselineDiff
from scripts.eval_harness.run_summary import RunSummary

# Off unless asked: a live model is gated by its baseline first.
DEFAULT_MIN_PASS_RATE: float = 0.0
# At most 2 of 100 played samples may assert what the data does not hold.
DEFAULT_MAX_HALLUCINATION_RATE: float = 0.02


@dataclass(frozen=True)
class GateLimits:
    min_pass_rate: float = DEFAULT_MIN_PASS_RATE
    max_hallucination_rate: float = DEFAULT_MAX_HALLUCINATION_RATE
    require_pass: bool = False


def find_gate_failures(
    summary: RunSummary, diff: BaselineDiff | None, limits: GateLimits
) -> list[str]:
    """Why the run fails, one line per gate; empty when it passes."""

    failures: list[str] = []
    if diff is not None and diff.is_regression:
        failures.append(
            "pass^k or a criterion's pass rate fell by more than its tolerance "
            "against the baseline"
        )

    if summary.stale_count:
        failures.append(
            f"{summary.stale_count} scenario(s) no longer match their cassette"
        )

    if summary.pass_rate < limits.min_pass_rate:
        failures.append(
            f"pass^k {summary.pass_rate:.1%} is under the floor "
            f"{limits.min_pass_rate:.1%}"
        )

    if summary.hallucination_rate > limits.max_hallucination_rate:
        failures.append(
            f"hallucination rate {summary.hallucination_rate:.1%} "
            f"({summary.hallucinated_count}/{summary.grounded_samples} samples) "
            f"is over the ceiling {limits.max_hallucination_rate:.1%}"
        )

    if limits.require_pass and summary.passed_count < summary.scenario_count:
        failures.append(
            f"{summary.scenario_count - summary.passed_count} scenario(s) failed "
            "and --require-pass is set"
        )

    return failures
