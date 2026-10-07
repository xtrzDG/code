"""
The scheduled guards CI cannot replace (the restore drill, the perf
budgets, the nightly evals) are themselves watched: every day a workflow
opens an issue for each one without a successful run in 8 days.
"""

import re
import subprocess
from pathlib import Path
from typing import Any, cast

import yaml

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
WORKFLOWS: Path = PROJECT_ROOT / ".github" / "workflows"
WATCHED: list[str] = ["restore-drill.yml", "perf.yml", "evals-nightly.yml"]


def load(path: Path) -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def watch_step() -> dict[str, Any]:
    workflow = load(WORKFLOWS / "schedule-watch.yml")
    [step] = cast(list[dict[str, Any]], workflow["jobs"]["watch"]["steps"])
    return step


def test_the_watch_runs_daily_and_by_hand_with_least_privilege() -> None:
    workflow = load(WORKFLOWS / "schedule-watch.yml")
    # YAML 1.1 reads the key `on` as True.
    triggers = cast(dict[str, Any], workflow.get("on", workflow.get(True)))
    job = workflow["jobs"]["watch"]

    assert triggers["schedule"] == [{"cron": "37 6 * * *"}]
    assert "workflow_dispatch" in triggers
    assert workflow["permissions"] == {"contents": "read"}
    assert job["permissions"] == {"actions": "read", "issues": "write"}
    assert "uses" not in watch_step()


def test_it_watches_every_scheduled_guard_for_eight_days() -> None:
    step = watch_step()
    watched: list[str] = str(step["env"]["WATCHED"]).split()

    assert watched == WATCHED
    assert step["env"]["MAX_AGE_DAYS"] == "8"
    for name in watched:
        guard = load(WORKFLOWS / name)
        triggers = cast(dict[str, Any], guard.get("on", guard.get(True)))
        assert triggers.get("schedule"), f"{name} has no schedule to watch"


def test_it_asks_for_successful_runs_and_opens_each_issue_once() -> None:
    script = str(watch_step()["run"])

    assert "gh run list --workflow" in script and "--status success" in script
    assert re.search(r'gh issue list --state open --search "in:title', script)
    assert "grep -Fxq" in script
    assert "gh issue create" in script


def test_the_script_is_valid_bash() -> None:
    completed = subprocess.run(
        ["bash", "-n"],
        input=str(watch_step()["run"]),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
