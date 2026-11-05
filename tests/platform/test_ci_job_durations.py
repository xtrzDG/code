"""The CI run's job durations: a summary table and warnings over 8 minutes."""

import io
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.ci_job_durations import (
    BUDGET_SECONDS,
    finished_jobs,
    format_seconds,
    main,
    render,
    wall_seconds,
)


def job(
    name: str,
    started: str | None,
    completed: str | None,
    *,
    status: str = "completed",
    conclusion: str | None = "success",
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "started_at": started,
        "completed_at": completed,
    }


RUN: dict[str, Any] = {
    "total_count": 6,
    "jobs": [
        job("Backend checks", "2026-10-05T10:00:00Z", "2026-10-05T10:04:30Z"),
        job(
            "End-to-end (2/4)",
            "2026-10-05T10:06:00Z",
            "2026-10-05T10:15:01Z",
            conclusion="failure",
        ),
        job("Backend tests (postgres)", "2026-10-05T10:00:05Z", "2026-10-05T10:08:00Z"),
        job(
            "Docker images",
            "2026-10-05T10:00:00Z",
            "2026-10-05T10:00:00Z",
            conclusion="skipped",
        ),
        job(
            "CI job durations",
            "2026-10-05T10:15:05Z",
            None,
            status="in_progress",
            conclusion=None,
        ),
        job("Queued", None, None, status="queued", conclusion=None),
    ],
}


def test_only_finished_jobs_count_slowest_first() -> None:
    jobs = finished_jobs(RUN)

    assert [(item.name, item.seconds) for item in jobs] == [
        ("End-to-end (2/4)", 541),
        ("Backend tests (postgres)", 475),
        ("Backend checks", 270),
    ]
    assert [item.is_over_budget for item in jobs] == [True, False, False]
    assert wall_seconds(jobs) == 901


def test_the_budget_is_eight_minutes_and_exactly_eight_is_within_it() -> None:
    run = {"jobs": [job("Edge", "2026-10-05T10:00:00Z", "2026-10-05T10:08:00Z")]}

    assert BUDGET_SECONDS == 480
    assert not finished_jobs(run)[0].is_over_budget


def test_the_summary_tables_every_job_and_marks_the_slow_ones() -> None:
    text = render(finished_jobs(RUN))

    assert "Wall time 15m 01s" in text
    assert "| End-to-end (2/4) | failure | **9m 01s, over budget** |" in text
    assert "| Backend tests (postgres) | success | 7m 55s |" in text
    assert "Docker images" not in text
    assert "| CI job durations |" not in text


def test_main_appends_the_summary_and_warns_per_slow_job(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    summary = tmp_path / "summary.md"
    summary.write_text("earlier steps\n", encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(RUN)))

    assert main(["--summary", str(summary)]) == 0

    assert summary.read_text(encoding="utf-8").startswith(
        "earlier steps\n### CI job durations"
    )
    assert capsys.readouterr().out.splitlines() == [
        "::warning title=Slow CI job::End-to-end (2/4) took 9m 01s, "
        "over the 8-minute budget per job."
    ]


def test_an_unreadable_input_is_reported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO('{"message": "Not Found"}'))

    assert main(["--summary", str(tmp_path / "summary.md")]) == 2
    assert "Cannot read the jobs" in capsys.readouterr().err


def test_a_name_with_a_pipe_keeps_the_table_intact() -> None:
    run = {"jobs": [job("a | b", "2026-10-05T10:00:00Z", "2026-10-05T10:00:09Z")]}

    assert "| a \\| b | success | 0m 09s |" in render(finished_jobs(run))
    assert format_seconds(0) == "0m 00s"
    assert wall_seconds([]) == 0
