"""Command-line options of scripts/run_evals.py."""

import argparse
from dataclasses import dataclass
from pathlib import Path

from app.schemas.typings.assistants.constrained_strings import LlmModelId
from scripts.eval_harness.baselines import DEFAULT_TOLERANCE
from scripts.eval_harness.eval_runner import (
    DEFAULT_TURN_LIMIT,
    SCRIPTED_MODEL,
    RunOptions,
)
from scripts.eval_harness.scenario_player import EvalMode, RunModels

EVALS_DIRECTORY: Path = Path("evals")
DESCRIPTION: str = """\
Evaluate the assistant over evals/datasets: every scenario is played
through the real conversation engine and scored by deterministic checks
(and a judge model when --judge-model is given).

Without --record the committed cassettes are replayed: no provider, no
key, the same answers every run (CI). A changed instruction, tool or
conversation path shows up as a stale cassette with the reason.
--record plays the scenarios with --model and writes new cassettes:
"scripted" plays each scenario's reference conversation offline; a real
model id (gpt-5-mini, claude-opus-5-5) needs OPENAI_API_KEY or
ANTHROPIC_API_KEY.
"""


@dataclass(frozen=True)
class CliOptions:
    run: RunOptions
    baselines_dir: Path
    out_dir: Path
    tolerance: float
    update_baseline: bool
    require_pass: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uv run python -m scripts.run_evals",
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--record", action="store_true", help="record cassettes")
    parser.add_argument("--niche", action="append", default=[], help="repeatable")
    parser.add_argument("--language", action="append", default=[], help="repeatable")
    parser.add_argument("--scenario", action="append", default=[], help="repeatable")
    parser.add_argument("--model", default=str(SCRIPTED_MODEL), help="assistant")
    parser.add_argument("--customer-model", help="AI customer (default: judge)")
    parser.add_argument("--judge-model", help="judge model (default: none)")
    parser.add_argument("--samples", type=int, default=1, help="k of pass^k")
    parser.add_argument("--turn-limit", type=int, default=DEFAULT_TURN_LIMIT)
    parser.add_argument("--datasets", type=Path, default=EVALS_DIRECTORY / "datasets")
    parser.add_argument("--cassettes", type=Path, default=EVALS_DIRECTORY / "cassettes")
    parser.add_argument("--baselines", type=Path, default=EVALS_DIRECTORY / "baselines")
    parser.add_argument("--out", type=Path, default=Path("reports") / "evals")
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    parser.add_argument(
        "--update-baseline", action="store_true", help="accept this run as baseline"
    )
    parser.add_argument(
        "--require-pass", action="store_true", help="fail when any scenario fails"
    )
    return parser


def parse_options(arguments: list[str] | None = None) -> CliOptions:
    parsed: argparse.Namespace = build_parser().parse_args(arguments)
    if parsed.samples < 1:
        raise SystemExit("--samples must be at least 1.")

    models: RunModels | None = None
    if parsed.record:
        judge: str | None = parsed.judge_model
        customer: str = parsed.customer_model or judge or parsed.model
        models = RunModels(
            assistant=LlmModelId(parsed.model),
            customer=LlmModelId(customer),
            judge=None if judge is None else LlmModelId(judge),
        )

    return CliOptions(
        run=RunOptions(
            datasets_dir=parsed.datasets,
            cassettes_dir=parsed.cassettes,
            mode=EvalMode.RECORD if parsed.record else EvalMode.REPLAY,
            models=models,
            niches=tuple(parsed.niche),
            languages=tuple(parsed.language),
            scenario_ids=tuple(parsed.scenario),
            samples=parsed.samples,
            turn_limit=parsed.turn_limit,
        ),
        baselines_dir=parsed.baselines,
        out_dir=parsed.out,
        tolerance=parsed.tolerance,
        update_baseline=parsed.update_baseline,
        require_pass=parsed.require_pass,
    )
