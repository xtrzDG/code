"""
CI's evals job replays every recorded conversation when a change touches
what the model sees (prompts, tool schemas, model pins, the engine, the
guard) or the harness, with a 100% floor and no hallucination, offline and
without keys, and "CI passed" (the required check) waits for it (AI-12).
"""

import io
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from scripts.eval_replay_scope import NULL_COMMIT, main, matching_paths

ROOT: Path = Path(__file__).resolve().parents[2]
CI: Path = ROOT / ".github" / "workflows" / "ci.yml"
NIGHTLY: Path = ROOT / ".github" / "workflows" / "evals-nightly.yml"


def jobs(path: Path) -> dict[str, Any]:
    document = cast(dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))
    return cast(dict[str, Any], document["jobs"])


@pytest.mark.parametrize(
    "path",
    [
        "app/utilities/assembly/instruction_rule_sections.py",
        "tests/assembly/snapshots/restaurant.chat.txt",
        "app/registries/tools/assistant_tool_catalog.py",
        "app/schemas/dto/assistant_tools.py",
        "app/schemas/dto/call_tool_inputs.py",
        "app/utilities/conversations/llm_model_pins.py",
        "app/use_cases/conversations/tools/call_tool_handlers.py",
        "app/utilities/reply_guard/invented_numbers.py",
        "evals/datasets/hotel.yaml",
        "scripts/eval_harness/grounding_check.py",
        "app/registries/localization/texts/en.json",
    ],
)
def test_a_model_facing_change_needs_the_replay(path: str) -> None:
    assert matching_paths([path]) == [path]


@pytest.mark.parametrize(
    "path",
    [
        "web/src/app/page.tsx",
        "app/gateways/http/booking_routes.py",
        "docs/operations/slo.md",
        "app/registries/localization/texts/it.json",
        "",
    ],
)
def test_other_changes_skip_it(path: str) -> None:
    assert matching_paths([path]) == []


def test_the_decision_goes_to_the_job_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr("sys.stdin", io.StringIO("README.md\nevals/README.md\n"))

    assert main([]) == 0
    assert main(["--all"]) == 0
    assert main(["--base", NULL_COMMIT]) == 0
    monkeypatch.setattr("sys.stdin", io.StringIO("web/package.json\n"))
    assert main([]) == 0

    assert output.read_text(encoding="utf-8").splitlines() == [
        "replay=true",
        "replay=true",
        "replay=true",
        "replay=false",
    ]
    assert "model-facing: evals/README.md" in capsys.readouterr().out


def test_an_unknown_base_commit_fails_the_job() -> None:
    assert main(["--base", "not-a-commit"]) == 2


def test_ci_replays_offline_with_a_full_floor_and_blocks_the_merge() -> None:
    ci = jobs(CI)
    job = cast(dict[str, Any], ci["evals"])
    script = "\n".join(str(step.get("run", "")) for step in job["steps"])

    assert "python3 scripts/eval_replay_scope.py" in script
    assert "--min-pass-rate 1" in script
    assert "--max-hallucination-rate 0" in script
    assert "--record" not in script
    assert (
        "secrets."
        not in CI.read_text(encoding="utf-8")
        .split("  evals:")[1]
        .split("\n  coverage:")[0]
    )
    assert "evals" in ci["ci-passed"]["needs"]


def test_the_nightly_run_has_a_floor_and_a_ceiling_too() -> None:
    script = "\n".join(
        str(step.get("run", "")) for step in jobs(NIGHTLY)["live"]["steps"]
    )

    assert '--min-pass-rate "$MIN_PASS_RATE"' in script
    assert '--max-hallucination-rate "$MAX_HALLUCINATION_RATE"' in script
