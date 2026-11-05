"""
Writes how long each test file's tests took, by group, for tests/durations.json.

With TEST_DURATIONS_REPORT=<file> (tests/conftest.py) the run's controller
(the only process under xdist that sees every test's report) adds up the
setup, call and teardown of every test per (group, file) and writes
{"postgres": {file: seconds}, "rest": {file: seconds}} when the session
ends; `uv run python -m scripts.backend_test_durations <reports>` merges such
reports into tests/durations.json (docs/operations/ci.md). CI writes one
per part and keeps it with the part's coverage data.
"""

import json
from collections import defaultdict
from pathlib import Path

import pytest

from tests.part_plan import GROUP_PROPERTY, GROUPS, REST_GROUP


class DurationRecorder:
    """A pytest plugin: seconds per (group, test file) of this run."""

    def __init__(self, report_path: Path) -> None:
        self._report_path: Path = report_path
        self._seconds: defaultdict[tuple[str, str], float] = defaultdict(float)

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        # tests/conftest.py names each test's group; xdist hands it over in the report.
        group: str = str(dict(report.user_properties).get(GROUP_PROPERTY, REST_GROUP))
        self._seconds[(group, report.nodeid.split("::", 1)[0])] += report.duration

    def pytest_sessionfinish(self) -> None:
        by_group: dict[str, dict[str, float]] = {group: {} for group in GROUPS}
        for (group, path), seconds in sorted(self._seconds.items()):
            by_group[group][path] = round(seconds, 2)
        self._report_path.parent.mkdir(parents=True, exist_ok=True)
        self._report_path.write_text(
            json.dumps(by_group, indent=2) + "\n", encoding="utf-8"
        )
