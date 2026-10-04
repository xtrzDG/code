"""
The evaluation harness (evals/README.md):

    uv run python -m scripts.run_evals                  # replay cassettes (CI)
    uv run python -m scripts.run_evals --record         # re-seed scripted cassettes
    uv run python -m scripts.run_evals --record --model gpt-5-mini \\
        --judge-model claude-opus-5-5 --samples 3 --cassettes reports/evals/cassettes

Writes reports/evals/report.json and report.html and compares the run with
evals/baselines/<model>.json. Exit code 1: the pass rate fell by more than
the tolerance, a replayed cassette is stale, or (with --require-pass) a
scenario failed.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

from scripts.eval_harness.baselines import (
    Baseline,
    BaselineDiff,
    baseline_path,
    build_baseline,
    compare_with_baseline,
    read_baseline,
    write_baseline,
)
from scripts.eval_harness.cli_options import CliOptions, parse_options
from scripts.eval_harness.dataset_loading import DatasetError
from scripts.eval_harness.eval_report import EvalReport, ModelsUsed
from scripts.eval_harness.eval_runner import RunOutcome, run_evals
from scripts.eval_harness.report_writing import write_reports
from scripts.eval_harness.run_results import ScenarioResult
from scripts.eval_harness.run_summary import RunSummary, summarize


def print_progress(scenario: ScenarioResult) -> None:
    status: str = (
        "PASS" if scenario.is_passed else "STALE" if scenario.is_stale else "FAIL"
    )
    print(f"{status:5} {scenario.key}", flush=True)


def main(arguments: list[str] | None = None) -> int:
    options: CliOptions = parse_options(arguments)
    try:
        outcome: RunOutcome = run_evals(options.run, print_progress)
    except DatasetError as error:
        print(f"Dataset error: {error}", file=sys.stderr)
        return 2

    summary: RunSummary = summarize(outcome.scenarios)
    assistant_models: set[str] = {str(m.assistant) for m in outcome.models.values()}
    judge_models: set[str] = {str(m.judge) for m in outcome.models.values() if m.judge}
    model_name: str = "+".join(sorted(assistant_models)) or "none"
    path: Path = baseline_path(options.baselines_dir, model_name)
    baseline: Baseline | None = read_baseline(path)
    diff: BaselineDiff | None = (
        None
        if baseline is None
        else compare_with_baseline(
            baseline, summary, outcome.scenarios, options.tolerance
        )
    )
    report = EvalReport(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        mode=options.run.mode.value,
        samples=options.run.samples,
        models=[
            ModelsUsed(
                niche=niche,
                assistant=str(models.assistant),
                customer=str(models.customer),
                judge=None if models.judge is None else str(models.judge),
            )
            for niche, models in sorted(outcome.models.items())
        ],
        summary=summary,
        baseline=diff,
        scenarios=outcome.scenarios,
    )
    written: list[Path] = write_reports(options.out_dir, report)
    if options.update_baseline:
        write_baseline(
            path,
            build_baseline(
                summary,
                outcome.scenarios,
                model_name,
                "+".join(sorted(judge_models)) or None,
                options.run.samples,
            ),
        )
        print(f"Baseline written: {path}")

    print(
        f"\npass^{options.run.samples} {summary.pass_rate:.1%} "
        f"({summary.passed_count}/{summary.scenario_count}), pass@1 "
        f"{summary.pass_at_1:.1%}, stale {summary.stale_count}, "
        f"cost ${summary.cost_usd:.4f}, model time p50 {summary.latency_p50_ms} ms "
        f"p95 {summary.latency_p95_ms} ms"
    )
    if diff is not None:
        print(
            f"baseline {diff.baseline_pass_rate:.1%} -> {diff.pass_rate:.1%} "
            f"({diff.delta * 100:+.1f} pt, tolerance {diff.tolerance * 100:.1f} pt)"
        )

    print("Report: " + ", ".join(str(item) for item in written))
    failed: bool = (
        (diff is not None and diff.is_regression)
        or summary.stale_count > 0
        or (options.require_pass and summary.passed_count < summary.scenario_count)
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
