"""
The weekly rescan's image-age report (scripts/image_age_report.py): each
pinned base image and the release commit with its age; over 30 days warns,
over 90 days fails, an unreadable time proves nothing.
"""

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from scripts.image_age_report import EXIT_FRESH, EXIT_STALE, EXIT_UNUSABLE, main

NOW: str = "2026-11-02T12:00:00Z"
PYTHON: str = "python:3.14-slim@sha256:" + "a" * 64


def age(tmp_path: Path, *arguments: str) -> tuple[int, str, str, str]:
    summary = tmp_path / "summary.md"
    output, errors = io.StringIO(), io.StringIO()
    with redirect_stdout(output), redirect_stderr(errors):
        code = main([*arguments, "--now", NOW, "--summary", str(summary)])
    text = summary.read_text(encoding="utf-8") if summary.exists() else ""
    return code, output.getvalue(), errors.getvalue(), text


def test_fresh_images_pass_with_a_table(tmp_path: Path) -> None:
    code, output, _, summary = age(
        tmp_path,
        f"{PYTHON}=2026-10-28T03:12:45.123456789Z",
        "--release-commit",
        "2026-10-30T12:00:00+00:00",
    )

    assert code == EXIT_FRESH
    assert "::" not in output
    assert f"| `{PYTHON}` | 2026-10-28 | 5 | fresh |" in summary
    assert "| `release (the commit production runs)` | 2026-10-30 | 3 | fresh |" in (
        summary
    )


def test_an_image_older_than_a_month_warns(tmp_path: Path) -> None:
    code, output, _, summary = age(tmp_path, f"{PYTHON}=2026-09-20T00:00:00Z")

    assert code == EXIT_FRESH
    assert f"::warning::{PYTHON} is 43 days old (more than 30)." in output
    assert "| 43 | older than 30 days |" in summary


def test_a_release_older_than_a_quarter_fails(tmp_path: Path) -> None:
    code, output, _, _ = age(
        tmp_path,
        f"{PYTHON}=2026-10-28T00:00:00Z",
        "--release-commit",
        "2026-07-01T00:00:00Z",
    )

    assert code == EXIT_STALE
    assert "::error::release (the commit production runs) is 124 days old" in output


def test_times_west_of_utc_are_read(tmp_path: Path) -> None:
    # git's %cI keeps the committer's offset; Docker may add nanoseconds.
    code, _, _, summary = age(
        tmp_path,
        f"{PYTHON}=2026-10-27T20:12:45.123456789-07:00",
        "--release-commit",
        "2026-10-30T07:00:00-05:00",
    )

    assert code == EXIT_FRESH
    assert f"| `{PYTHON}` | 2026-10-27 | 5 | fresh |" in summary
    assert "| 2026-10-30 | 3 | fresh |" in summary


@pytest.mark.parametrize(
    "arguments",
    [
        (f"{PYTHON}=yesterday",),
        (f"{PYTHON}=2026-10-28T00:00:00",),
        ("2026-10-28T00:00:00Z",),
        (),
    ],
)
def test_an_unreadable_argument_proves_nothing(
    tmp_path: Path, arguments: tuple[str, ...]
) -> None:
    code, _, errors, summary = age(tmp_path, *arguments)

    assert (code, summary) == (EXIT_UNUSABLE, "")
    assert "::error::Image age:" in errors
