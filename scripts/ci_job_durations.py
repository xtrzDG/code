"""
How long each job of a CI run took, for the run's summary
(.github/workflows/ci.yml, job "durations"):

    gh api "repos/OWNER/REPO/actions/runs/RUN_ID/attempts/ATTEMPT/jobs" \\
        | uv run --no-project python -m scripts.ci_job_durations \\
            --summary "$GITHUB_STEP_SUMMARY"

Reads the jobs JSON of the GitHub API from stdin, appends a Markdown table
(slowest first, with the run's wall time) to the summary file, and prints a
`::warning` workflow command for every job over the 8-minute budget. Jobs
still running (this one) or skipped are left out. Exit codes: 0 always for
a readable input (slowness warns, never fails), 2 for an unreadable one.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

BUDGET_SECONDS: int = 8 * 60
EXIT_OK: int = 0
EXIT_UNUSABLE: int = 2


@dataclass(frozen=True)
class JobDuration:
    """One finished job: its name, conclusion and start and end."""

    name: str
    conclusion: str
    started_at: datetime
    completed_at: datetime

    @property
    def seconds(self) -> int:
        return max(0, round((self.completed_at - self.started_at).total_seconds()))

    @property
    def is_over_budget(self) -> bool:
        return self.seconds > BUDGET_SECONDS


def format_seconds(seconds: int) -> str:
    minutes, rest = divmod(seconds, 60)
    return f"{minutes}m {rest:02d}s"


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def finished_jobs(payload: dict[str, Any]) -> list[JobDuration]:
    jobs: list[JobDuration] = []
    for job in payload["jobs"]:
        started: str | None = job.get("started_at")
        completed: str | None = job.get("completed_at")
        conclusion: str = str(job.get("conclusion") or "")
        if (
            job.get("status") != "completed"
            or not started
            or not completed
            or conclusion == "skipped"
        ):
            continue

        jobs.append(
            JobDuration(
                name=str(job["name"]),
                conclusion=conclusion,
                started_at=parse_time(started),
                completed_at=parse_time(completed),
            )
        )
    return sorted(jobs, key=lambda job: (-job.seconds, job.name))


def wall_seconds(jobs: list[JobDuration]) -> int:
    if not jobs:
        return 0

    first: datetime = min(job.started_at for job in jobs)
    last: datetime = max(job.completed_at for job in jobs)
    return max(0, round((last - first).total_seconds()))


def cell(text: str) -> str:
    return text.replace("|", "\\|")


def render(jobs: list[JobDuration]) -> str:
    lines: list[str] = [
        "### CI job durations",
        "",
        f"Wall time {format_seconds(wall_seconds(jobs))} (first job start to "
        f"last job end); budget per job {format_seconds(BUDGET_SECONDS)}.",
        "",
        "| job | result | duration |",
        "| --- | --- | ---: |",
    ]
    for job in jobs:
        duration: str = format_seconds(job.seconds)
        if job.is_over_budget:
            duration = f"**{duration}, over budget**"
        lines.append(f"| {cell(job.name)} | {job.conclusion} | {duration} |")
    return "\n".join(lines) + "\n"


def warnings(jobs: list[JobDuration]) -> list[str]:
    return [
        f"::warning title=Slow CI job::{job.name} took "
        f"{format_seconds(job.seconds)}, over the "
        f"{BUDGET_SECONDS // 60}-minute budget per job."
        for job in jobs
        if job.is_over_budget
    ]


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ci_job_durations")
    parser.add_argument("--summary", type=Path, required=True)
    parsed: argparse.Namespace = parser.parse_args(arguments)
    try:
        jobs: list[JobDuration] = finished_jobs(json.load(sys.stdin))
    except (ValueError, KeyError, TypeError) as error:
        print(f"Cannot read the jobs: {error!r}", file=sys.stderr)
        return EXIT_UNUSABLE

    with parsed.summary.open("a", encoding="utf-8") as summary:
        summary.write(render(jobs))
    for line in warnings(jobs):
        print(line)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
