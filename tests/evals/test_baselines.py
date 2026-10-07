"""Baselines: what a model scored, compared scenario by scenario."""

from pathlib import Path

from scripts.eval_harness.baselines import (
    baseline_path,
    build_baseline,
    compare_with_baseline,
    read_baseline,
    write_baseline,
)
from scripts.eval_harness.run_results import ScenarioResult
from scripts.eval_harness.run_summary import summarize
from tests.evals.result_builders import sample, scenario


def run(*passed: bool) -> list[ScenarioResult]:
    languages = [
        "en",
        "ka",
        "ru",
        "he",
        "ar",
        *(f"qa{chr(97 + index)}" for index in range(20)),
    ]
    return [
        scenario("hotel", languages[index], [sample(ok)])
        for index, ok in enumerate(passed)
    ]


def test_a_baseline_round_trips(tmp_path: Path) -> None:
    scenarios = run(True, False)
    baseline = build_baseline(summarize(scenarios), scenarios, "gpt-5-mini", None, 3)
    path = baseline_path(tmp_path / "baselines", "gpt-5-mini")

    write_baseline(path, baseline)

    assert read_baseline(path) == baseline
    assert read_baseline(tmp_path / "missing.json") is None
    assert baseline.scenarios == {"hotel/price__en": True, "hotel/price__ka": False}


def test_a_drop_beyond_the_tolerance_is_a_regression() -> None:
    before = run(True, True, True, True)
    baseline = build_baseline(summarize(before), before, "scripted", None, 1)
    after = run(True, False, True, True)

    diff = compare_with_baseline(baseline, summarize(after), after, tolerance=0.2)
    strict = compare_with_baseline(baseline, summarize(after), after, tolerance=0.1)

    assert (diff.baseline_pass_rate, diff.pass_rate, diff.delta) == (1.0, 0.75, -0.25)
    assert diff.is_regression and strict.is_regression
    assert diff.newly_failing == ["hotel/price__ka"]
    assert diff.criteria_deltas["prices"] == -0.25


def test_a_subset_compares_only_shared_scenarios() -> None:
    before = run(True, False, True)
    baseline = build_baseline(summarize(before), before, "scripted", None, 1)
    subset = [scenario("hotel", "ka", [sample(True)])]

    diff = compare_with_baseline(baseline, summarize(subset), subset, tolerance=0.05)

    assert diff.compared_scenarios == 1
    assert (diff.baseline_pass_rate, diff.pass_rate) == (0.0, 1.0)
    assert diff.newly_passing == ["hotel/price__ka"]
    assert not diff.is_regression
    # Criteria compare over the scenarios both runs played.
    assert diff.criteria_deltas == {"language": 0.0, "prices": 1.0}


def test_a_criterion_drop_beyond_its_tolerance_is_a_regression() -> None:
    before = run(*[True] * 20)
    baseline = build_baseline(summarize(before), before, "scripted", None, 1)
    # One price failure in 20 (5 points), still within a 10-point pass-rate
    # tolerance but beyond the 3-point criterion tolerance.
    after = [*run(*[True] * 19), scenario("hotel", "qzz", [sample(False)])]
    baseline.scenarios["hotel/price__qzz"] = True
    baseline.scenario_criteria["hotel/price__qzz"] = {"language": 1.0, "prices": 1.0}

    diff = compare_with_baseline(baseline, summarize(after), after, tolerance=0.1)
    lenient = compare_with_baseline(
        baseline, summarize(after), after, tolerance=0.1, criterion_tolerance=0.1
    )

    assert diff.delta == -0.05
    assert diff.criteria_deltas["prices"] == -0.05
    assert diff.regressed_criteria == ["prices"] and diff.is_regression
    assert lenient.regressed_criteria == [] and not lenient.is_regression


def test_an_older_baseline_compares_criteria_only_over_the_same_set() -> None:
    before = run(True, True)
    baseline = build_baseline(summarize(before), before, "scripted", None, 1)
    baseline.scenario_criteria.clear()
    subset = run(True)

    same = compare_with_baseline(baseline, summarize(before), before)
    partial = compare_with_baseline(baseline, summarize(subset), subset)

    assert same.criteria_deltas == {"language": 0.0, "prices": 0.0}
    assert partial.criteria_deltas == {}
