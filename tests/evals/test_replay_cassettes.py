"""
The CI gate of the evaluation harness: every dataset scenario replays from
its committed cassette through the real conversation engine and scores as
the accepted baseline says (evals/baselines/scripted.json).

A stale cassette means the instruction, the tools or the conversation path
changed since it was recorded; the failure shows what changed. After an
intended change, re-record the scripted cassettes and review their diff:

    uv run python -m scripts.run_evals --record --update-baseline
"""

from pathlib import Path

import pytest

from scripts.eval_harness.baselines import Baseline, read_baseline
from scripts.eval_harness.dataset_loading import list_dataset_paths
from scripts.eval_harness.eval_runner import RunOptions, RunOutcome, run_evals
from scripts.eval_harness.run_results import ScenarioResult
from scripts.eval_harness.scenario_player import EvalMode

EVALS: Path = Path(__file__).resolve().parents[2] / "evals"
RECORD_COMMAND: str = "uv run python -m scripts.run_evals --record --update-baseline"
NICHES: list[str] = [path.stem for path in list_dataset_paths(EVALS / "datasets")]


def describe_failure(scenario: ScenarioResult) -> str:
    sample = scenario.samples[0]
    reasons: list[str] = list(sample.stale_reasons) or [
        f"{result.criterion.value}: {' '.join(str(note) for note in result.notes)}"
        for result in sample.criteria
        if not result.is_passed
    ]
    return f"{scenario.key}:\n  " + "\n  ".join(reasons or [str(sample.error)])


@pytest.mark.parametrize("niche", NICHES)
def test_the_cassettes_replay_as_the_baseline_says(niche: str) -> None:
    baseline: Baseline | None = read_baseline(EVALS / "baselines" / "scripted.json")
    assert baseline is not None, "evals/baselines/scripted.json is missing."

    outcome: RunOutcome = run_evals(
        RunOptions(
            datasets_dir=EVALS / "datasets",
            cassettes_dir=EVALS / "cassettes",
            mode=EvalMode.REPLAY,
            models=None,
            niches=(niche,),
        )
    )

    stale = [describe_failure(s) for s in outcome.scenarios if s.is_stale]
    assert not stale, (
        f"{len(stale)} scenario(s) of {niche} no longer match their cassette. "
        f"If the change is intended, run `{RECORD_COMMAND}`.\n\n" + "\n\n".join(stale)
    )
    changed = [
        describe_failure(scenario)
        for scenario in outcome.scenarios
        if baseline.scenarios.get(scenario.key) is not scenario.is_passed
    ]
    assert not changed, (
        "These scenarios score differently from the baseline:\n\n"
        + "\n\n".join(changed)
    )


def test_every_dataset_has_a_cassette_and_a_baseline_entry() -> None:
    cassettes = {path.stem for path in (EVALS / "cassettes").glob("*.json")}
    baseline = read_baseline(EVALS / "baselines" / "scripted.json")

    assert cassettes == set(NICHES)
    assert baseline is not None
    assert {key.split("/")[0] for key in baseline.scenarios} == set(NICHES)
