"""The weekly perf run fails on a p95 more than 20% above the baseline."""

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.perf_compare import Comparison, main

ROOT: Path = Path(__file__).resolve().parents[2]


def report(**p95_ms: float) -> dict[str, Any]:
    return {
        "scale": {"name": "full"},
        "results": {name: {"p95_ms": value} for name, value in p95_ms.items()},
    }


def write(path: Path, document: dict[str, Any]) -> Path:
    path.write_text(json.dumps(document))
    return path


@pytest.mark.parametrize(
    ("baseline", "measured", "regressed"),
    [
        (100.0, 120.0, False),
        (100.0, 120.5, True),
        (2.0, 2.9, False),  # +45%, but within the 1 ms of timer noise
        (2.0, 3.5, True),
        (50.0, None, True),
        (None, 80.0, False),
    ],
)
def test_a_regression_is_over_20_percent_and_1_ms(
    baseline: float | None, measured: float | None, regressed: bool
) -> None:
    assert Comparison("dashboard", baseline, measured).is_regression is regressed


def test_the_run_fails_on_a_regression_and_prints_the_table(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    baseline = write(
        tmp_path / "baseline.json",
        {"scale": "full", "p95_ms": {"dashboard": 100.0, "widget_poll": 10.0}},
    )
    fine = write(tmp_path / "fine.json", report(dashboard=110.0, widget_poll=9.0))
    slow = write(tmp_path / "slow.json", report(dashboard=130.0, widget_poll=9.0))

    assert main([str(fine), str(baseline)]) == 0
    assert main([str(slow), str(baseline)]) == 1
    output = capsys.readouterr().out
    assert "| dashboard | 100.0 | 130.0 | +30% | regression |" in output
    assert "| widget_poll | 10.0 | 9.0 | -10% | ok |" in output


def test_another_scale_or_a_broken_file_cannot_be_compared(tmp_path: Path) -> None:
    baseline = write(tmp_path / "baseline.json", {"scale": "small", "p95_ms": {}})
    measured = write(tmp_path / "report.json", report(dashboard=1.0))
    broken = tmp_path / "broken.json"
    broken.write_text("{")

    assert main([str(measured), str(baseline)]) == 2
    assert main([str(broken), str(baseline)]) == 2


def test_update_stores_the_report_as_the_baseline(tmp_path: Path) -> None:
    measured = write(
        tmp_path / "report.json", report(dashboard=41.26, authenticate=9.04)
    )
    baseline = tmp_path / "baseline.json"

    assert main([str(measured), str(baseline), "--update"]) == 0
    assert json.loads(baseline.read_text()) == {
        "scale": "full",
        "p95_ms": {"authenticate": 9.0, "dashboard": 41.3},
    }


def test_the_stored_baseline_names_every_budgeted_request() -> None:
    from tests.perf.test_latency_budgets import BUDGETS_MS

    stored = json.loads((ROOT / "perf" / "baseline.json").read_text())

    assert stored["scale"] == "full"
    assert sorted(stored["p95_ms"]) == sorted(BUDGETS_MS)
    for name, value in stored["p95_ms"].items():
        assert 0 < value <= BUDGETS_MS[name], name
