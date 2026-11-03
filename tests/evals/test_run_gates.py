"""
What fails a run: a regression against the baseline, a stale cassette, a
pass rate under the floor, a hallucination rate over the ceiling, and with
--require-pass any failed scenario; and the summary counts hallucinations
over the samples that were played to the end.
"""

from scripts.eval_harness.baselines import BaselineDiff, build_baseline
from scripts.eval_harness.cli_options import parse_options
from scripts.eval_harness.run_gates import (
    DEFAULT_MAX_HALLUCINATION_RATE,
    GateLimits,
    find_gate_failures,
)
from scripts.eval_harness.run_results import SampleResult
from scripts.eval_harness.run_summary import RunSummary, summarize
from tests.evals.result_builders import sample, scenario


def hallucinated(passed: bool = True, stale: bool = False) -> SampleResult:
    result: SampleResult = sample(passed, stale=stale)
    return result.model_copy(update={"hallucinations": ["A reply asserts 'yes'."]})


def summary_of(*samples: SampleResult) -> RunSummary:
    return summarize(
        [scenario(f"niche{index}", "en", [item]) for index, item in enumerate(samples)]
    )


def test_the_summary_counts_hallucinations_over_played_samples() -> None:
    summary = summary_of(
        hallucinated(),
        sample(True),
        sample(True),
        hallucinated(stale=True),
    )

    assert (summary.grounded_samples, summary.hallucinated_count) == (3, 1)
    assert summary.hallucination_rate == 0.3333
    assert build_baseline(summary, [], "scripted", None, 1).hallucination_rate == 0.3333


def test_a_clean_run_passes_every_gate() -> None:
    summary = summary_of(sample(True), sample(True))

    assert find_gate_failures(summary, None, GateLimits(min_pass_rate=1.0)) == []


def test_each_gate_names_why_the_run_fails() -> None:
    summary = summary_of(hallucinated(), sample(False), sample(True, stale=True))
    regression = BaselineDiff(
        baseline_pass_rate=1.0,
        pass_rate=0.5,
        delta=-0.5,
        tolerance=0.03,
        is_regression=True,
        compared_scenarios=2,
    )

    failures = find_gate_failures(
        summary,
        regression,
        GateLimits(min_pass_rate=0.9, max_hallucination_rate=0.0, require_pass=True),
    )

    assert failures == [
        "pass^k or a criterion's pass rate fell by more than its tolerance "
        "against the baseline",
        "1 scenario(s) no longer match their cassette",
        "pass^k 66.7% is under the floor 90.0%",
        "hallucination rate 50.0% (1/2 samples) is over the ceiling 0.0%",
        "1 scenario(s) failed and --require-pass is set",
    ]


def test_the_ceiling_allows_two_hallucinations_in_a_hundred_by_default() -> None:
    samples = [hallucinated(), hallucinated()] + [sample(True)] * 98
    defaults = parse_options([]).limits

    assert defaults.max_hallucination_rate == DEFAULT_MAX_HALLUCINATION_RATE
    assert defaults.min_pass_rate == 0.0
    assert find_gate_failures(summary_of(*samples), None, defaults) == []
    assert find_gate_failures(summary_of(*samples, hallucinated()), None, defaults)


def test_the_cli_reads_the_floor_and_the_ceiling() -> None:
    limits = parse_options(
        ["--min-pass-rate", "1", "--max-hallucination-rate", "0", "--require-pass"]
    ).limits

    assert limits == GateLimits(
        min_pass_rate=1.0, max_hallucination_rate=0.0, require_pass=True
    )
