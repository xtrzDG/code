"""
Every workflow job runs on a named Ubuntu release, never on `ubuntu-latest`.

On 26 October 2026 GitHub moved `ubuntu-latest` to Ubuntu 26.04, which has
no `postgresql-16`: the Postgres tests stopped before their first test, and
the system packages the end-to-end shards cache are keyed to the 24.04
image. Moving to a newer release is a change of its own
(docs/operations/ci.md, "The jobs").
"""

from pathlib import Path
from typing import Any, cast

import yaml

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
WORKFLOW_DIRECTORY: Path = PROJECT_ROOT / ".github" / "workflows"
RUNNER: str = "ubuntu-24.04"


def jobs_and_runners() -> list[tuple[str, object]]:
    runners: list[tuple[str, object]] = []
    for path in sorted(WORKFLOW_DIRECTORY.glob("*.yml")):
        workflow = cast(
            dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8"))
        )
        jobs = cast(dict[str, dict[str, Any]], workflow.get("jobs", {}))
        runners.extend(
            (f"{path.name}:{name}", job.get("runs-on")) for name, job in jobs.items()
        )
    return runners


def test_every_job_runs_on_the_named_ubuntu_release() -> None:
    runners = jobs_and_runners()
    elsewhere = [
        f"{job} runs on {runner!r}" for job, runner in runners if runner != RUNNER
    ]

    assert len(runners) > 20
    assert elsewhere == []
