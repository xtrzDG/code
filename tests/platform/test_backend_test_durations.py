"""
Test durations are measured by the run itself and merged into tests/durations.json.

tests/duration_recorder.py writes a run's seconds per (group, test file);
scripts/backend_test_durations.py merges such reports (one per CI part)
into the committed file the parts are planned from.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import pytest

from scripts.backend_test_durations import (
    EXIT_OK,
    EXIT_UNUSABLE,
    main,
    merge_durations,
    read_report,
)
from tests.duration_recorder import DurationRecorder
from tests.part_plan import GROUP_PROPERTY

EXISTING_FILE: str = "tests/platform/test_backend_test_durations.py"


@dataclass
class FakeReport:
    """The parts of a test report the recorder reads (xdist hands lists over)."""

    nodeid: str
    duration: float
    user_properties: list[Any] = field(default_factory=list[Any])


def test_the_recorder_adds_up_each_files_setup_call_and_teardown_by_group(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "reports" / "durations-rest-1.json"
    recorder = DurationRecorder(report_path)
    for report in (
        FakeReport("tests/a.py::one", 0.5, [(GROUP_PROPERTY, "rest")]),
        FakeReport("tests/a.py::one", 1.25, [[GROUP_PROPERTY, "rest"]]),
        FakeReport("tests/a.py::Two::three[x]", 0.25, [(GROUP_PROPERTY, "rest")]),
        FakeReport("tests/a.py::pg", 3.0, [(GROUP_PROPERTY, "postgres")]),
        FakeReport("tests/b.py::four", 0.111, []),
    ):
        recorder.pytest_runtest_logreport(cast(pytest.TestReport, report))

    recorder.pytest_sessionfinish()

    assert json.loads(report_path.read_text(encoding="utf-8")) == {
        "postgres": {"tests/a.py": 3.0},
        "rest": {"tests/a.py": 2.0, "tests/b.py": 0.11},
    }


def test_a_report_must_map_the_groups_to_seconds(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    for text, message in (
        ('{"other": {}}', "must map the groups"),
        ('{"rest": []}', "must map test files to seconds"),
        ('{"rest": {"tests/a.py": -1}}', "number of seconds"),
        ('{"rest": {"tests/a.py": true}}', "number of seconds"),
    ):
        path.write_text(text, encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            read_report(path)
    path.write_text('{"rest": {"tests/a.py": 2}}', encoding="utf-8")

    assert read_report(path) == {"postgres": {}, "rest": {"tests/a.py": 2.0}}


def test_measured_files_replace_their_entries_and_files_that_are_gone_are_dropped() -> (
    None
):
    merged = merge_durations(
        {
            "rest": {"tests/a.py": 30.0, "tests/b.py": 6.0, "tests/gone.py": 12.0},
            "postgres": {"tests/a.py": 1.0},
        },
        [
            {"rest": {"tests/a.py": 4.567}, "postgres": {}},
            {"rest": {"tests/c.py": 2.0}, "postgres": {}},
        ],
        {"tests/a.py", "tests/b.py", "tests/c.py"},
    )

    assert merged == {
        "postgres": {"tests/a.py": 1.0},
        "rest": {"tests/a.py": 4.57, "tests/b.py": 6.0, "tests/c.py": 2.0},
    }


def test_the_script_merges_reports_into_the_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "durations.json"
    output.write_text(
        json.dumps(
            {"postgres": {}, "rest": {EXISTING_FILE: 9.0, "tests/gone.py": 1.0}}
        ),
        encoding="utf-8",
    )
    report = tmp_path / "durations-rest-1.json"
    report.write_text(json.dumps({"rest": {EXISTING_FILE: 0.5}}), encoding="utf-8")

    assert main([str(report), "--output", str(output)]) == EXIT_OK

    assert json.loads(output.read_text(encoding="utf-8")) == {
        "postgres": {},
        "rest": {EXISTING_FILE: 0.5},
    }
    assert "1 measured entries merged" in capsys.readouterr().out


def test_the_script_refuses_an_unreadable_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "durations.json"
    report = tmp_path / "broken.json"
    report.write_text("{not json", encoding="utf-8")

    assert main([str(report), "--output", str(output)]) == EXIT_UNUSABLE
    assert not output.exists()
    assert capsys.readouterr().err
