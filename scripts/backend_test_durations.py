"""
Merges duration reports of backend test runs into tests/durations.json, which
CI balances its backend test parts by (tests/part_plan.py):

    TEST_DURATIONS_REPORT=durations-report.json uv run pytest -n auto \\
        --cov=app --cov-branch --cov-report= --cov-fail-under=0
    uv run python -m scripts.backend_test_durations durations-report.json

A report holds {"postgres": {file: seconds}, "rest": {file: seconds}}
(tests/duration_recorder.py). CI writes one per part into the part's
`coverage-<group>-<part>` artifact, so the reports of a CI run give the
durations measured on CI's own machines. A file a report measured replaces
its entry, entries of test files that no longer exist are dropped, every
other entry stays. Exit codes: 0 written, 2 for an unreadable report.
"""

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import cast

GROUPS: tuple[str, ...] = ("postgres", "rest")
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
DURATIONS_PATH: Path = PROJECT_ROOT / "tests" / "durations.json"
EXIT_OK: int = 0
EXIT_UNUSABLE: int = 2
DESCRIPTION: str = "Merges backend test duration reports into tests/durations.json."


def read_report(path: Path) -> dict[str, dict[str, float]]:
    """A report's seconds per file, by group; ValueError when it is not one."""
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must map the groups {', '.join(GROUPS)} to files.")
    table = cast(dict[object, object], raw)
    if not set(table) <= set(GROUPS):
        raise ValueError(f"{path} must map the groups {', '.join(GROUPS)} to files.")
    report: dict[str, dict[str, float]] = {group: {} for group in GROUPS}
    for group, files in table.items():
        if not isinstance(files, dict):
            raise ValueError(f"{path}: {group} must map test files to seconds.")
        for name, seconds in cast(dict[object, object], files).items():
            if (
                isinstance(seconds, bool)
                or not isinstance(seconds, int | float)
                or seconds < 0
            ):
                raise ValueError(f"{path}: {group} {name} must be a number of seconds.")
            report[str(group)][str(name)] = float(seconds)
    return report


def merge_durations(
    previous: Mapping[str, Mapping[str, float]],
    reports: list[dict[str, dict[str, float]]],
    existing_files: set[str],
) -> dict[str, dict[str, float]]:
    """Measured files replace their entries; files that are gone are dropped."""
    merged: dict[str, dict[str, float]] = {}
    for group in GROUPS:
        entries: dict[str, float] = dict(previous.get(group, {}))
        for report in reports:
            entries.update(report.get(group, {}))
        merged[group] = {
            name: round(seconds, 2)
            for name, seconds in sorted(entries.items())
            if name in existing_files
        }
    return merged


def existing_test_files(root: Path) -> set[str]:
    """Every test module under tests/, as the paths reports name them."""
    return {
        path.relative_to(root).as_posix()
        for path in (root / "tests").rglob("test_*.py")
    }


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "reports", nargs="+", type=Path, help="duration reports to merge"
    )
    parser.add_argument("--output", type=Path, default=DURATIONS_PATH)
    options = parser.parse_args(arguments)

    try:
        reports = [read_report(path) for path in options.reports]
        previous = read_report(options.output) if options.output.exists() else {}
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return EXIT_UNUSABLE
    merged = merge_durations(previous, reports, existing_test_files(PROJECT_ROOT))
    options.output.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    measured: int = sum(len(report[group]) for report in reports for group in GROUPS)
    print(f"{options.output.name}: {measured} measured entries merged.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
