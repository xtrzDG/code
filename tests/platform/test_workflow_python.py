"""
Repository Python in the workflows runs on uv's Python 3.14, never on the
runner image's own python3 (3.12 on ubuntu-24.04): the code is written
for 3.14 (ruff's target), and the formatter writes syntax older
interpreters refuse (`except A, B:`). The weekly load run once stopped
there, before its scenarios (scripts/perf_runner.py).
"""

import re
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
WORKFLOW_DIRECTORY: Path = PROJECT_ROOT / ".github" / "workflows"
# A command of a step: lines, pipes and lists split a shell script into them.
COMMAND_SEPARATOR: re.Pattern[str] = re.compile(r"\n|\|\|?|;|&&")
# An interpreter started on the repository's modules or scripts.
REPOSITORY_PYTHON: re.Pattern[str] = re.compile(
    r"\bpython3?(?:\.\d+)?\s+(?:-[A-Za-z]+\s+)*(?:-m\s+)?(?:scripts|app|tests)[./]"
)
UV_RUN: str = "uv run"


def workflow_paths() -> list[Path]:
    return sorted(WORKFLOW_DIRECTORY.glob("*.yml"))


def step_commands(workflow_path: Path) -> list[tuple[str, str]]:
    """(job, command) of every shell command of the workflow's steps."""

    workflow = cast(dict[str, Any], yaml.safe_load(workflow_path.read_text()))
    commands: list[tuple[str, str]] = []
    for job_name, job in cast(dict[str, Any], workflow["jobs"]).items():
        for step in cast(list[dict[str, Any]], job.get("steps", [])):
            script: str = str(step.get("run", ""))
            commands.extend(
                (str(job_name), command.strip())
                for command in COMMAND_SEPARATOR.split(script)
            )
    return commands


def runs_on_image_python(command: str) -> bool:
    return any(
        UV_RUN not in command[: match.start()]
        for match in REPOSITORY_PYTHON.finditer(command)
    )


@pytest.mark.parametrize("workflow_path", workflow_paths(), ids=lambda path: path.name)
def test_repository_python_runs_through_uv(workflow_path: Path) -> None:
    offending: list[str] = [
        f"{job}: {command}"
        for job, command in step_commands(workflow_path)
        if runs_on_image_python(command)
    ]

    assert offending == []


def test_the_check_tells_the_image_python_from_uv() -> None:
    assert runs_on_image_python("python3 -m scripts.perf_runner --seed-seconds 1")
    assert runs_on_image_python("python -B scripts/check.py")
    assert runs_on_image_python("python3.12 -m app.gateways.cli.migrate")
    assert not runs_on_image_python(
        "uv run --no-project python -m scripts.perf_runner --seed-seconds 1"
    )
    assert not runs_on_image_python("uv run python -m app.gateways.cli.migrate")
    assert not runs_on_image_python(
        "docker run --rm --entrypoint python assistant-workshop-backend:ci -c"
    )
