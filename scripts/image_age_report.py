"""
The image-age report of the weekly rescan (.github/workflows/image-rescan.yml):
how old each pinned base image is (its `Created`) and how long ago the
commit production runs was made, as a table in the run summary:

    uv run --no-project python -m scripts.image_age_report \\
        --summary "$GITHUB_STEP_SUMMARY" --release-commit 2026-10-30T12:00:00Z \\
        "python:3.14-slim@sha256:...=2026-10-28T03:12:00Z" ...

A base image takes Debian's and Node's fixes only when it is rebuilt, and
production's image only when it is deployed again: older than 30 days is a
warning (Dependabot's docker updates or a deploy are due), older than 90
days fails the run. Exit codes: 0 everything younger than 90 days, 1 an
image or the release older, 2 an argument that cannot be read.
"""

import argparse
import datetime
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

EXIT_FRESH: int = 0
EXIT_STALE: int = 1
EXIT_UNUSABLE: int = 2
WARNING_DAYS: int = 30
FAILING_DAYS: int = 90


@dataclass(frozen=True)
class Aged:
    name: str
    created: datetime.datetime

    def days(self, now: datetime.datetime) -> int:
        return (now - self.created).days


def timestamp(value: str) -> datetime.datetime:
    """An RFC 3339 time (Docker's `Created` has nanoseconds and a Z; git's
    committer time an offset, east or west of UTC)."""

    parsed = datetime.datetime.fromisoformat(value.strip())
    if parsed.tzinfo is None:
        raise ValueError(f"{value!r} names no time zone")
    return parsed


def image(value: str) -> Aged:
    name, separator, created = value.rpartition("=")
    if not separator or not name:
        raise ValueError(f"{value!r}: expected <image>=<created>")
    return Aged(name=name, created=timestamp(created))


def verdict(days: int) -> str:
    if days > FAILING_DAYS:
        return f"older than {FAILING_DAYS} days"
    if days > WARNING_DAYS:
        return f"older than {WARNING_DAYS} days"
    return "fresh"


def report(aged: Sequence[Aged], now: datetime.datetime) -> list[str]:
    lines = [
        "## Image age",
        "",
        "| What | Created | Age (days) | |",
        "| --- | --- | --- | --- |",
    ]
    for each in aged:
        days = each.days(now)
        lines.append(
            f"| `{each.name}` | {each.created.date().isoformat()} | {days}"
            f" | {verdict(days)} |"
        )
    return lines


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="How old the images are.")
    parser.add_argument("images", nargs="*", help="<image>=<created>")
    parser.add_argument("--release-commit", help="the release commit's time")
    parser.add_argument("--now", help="the time to measure from (tests)")
    parser.add_argument("--summary", type=Path)
    parsed = parser.parse_args(arguments)
    try:
        aged = [image(value) for value in parsed.images]
        if parsed.release_commit:
            aged.append(
                Aged(
                    "release (the commit production runs)",
                    timestamp(parsed.release_commit),
                )
            )
        now = (
            timestamp(parsed.now) if parsed.now else datetime.datetime.now(datetime.UTC)
        )
    except ValueError as error:
        print(f"::error::Image age: {error}", file=sys.stderr)
        return EXIT_UNUSABLE
    if not aged:
        print("::error::Image age: no image to measure", file=sys.stderr)
        return EXIT_UNUSABLE

    stale = False
    for each in aged:
        days = each.days(now)
        if days > FAILING_DAYS:
            stale = True
            print(
                f"::error::{each.name} is {days} days old (more than {FAILING_DAYS})."
            )
        elif days > WARNING_DAYS:
            print(
                f"::warning::{each.name} is {days} days old (more than {WARNING_DAYS})."
            )
    if parsed.summary is not None:
        with parsed.summary.open("a", encoding="utf-8") as summary:
            summary.write("\n".join(report(aged, now)) + "\n")
    return EXIT_STALE if stale else EXIT_FRESH


if __name__ == "__main__":
    sys.exit(main())
