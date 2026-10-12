"""
The weekly perf run shows its runner next to the numbers (CPUs, model,
memory, seed time) and lets the worker drain between the load scenarios.
"""

import io
import json
from pathlib import Path
from typing import Any, cast

import yaml

from scripts.perf_runner import cpu_model, main, memory_gib, read_report, render

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
PERF_WORKFLOW: Path = PROJECT_ROOT / ".github" / "workflows" / "perf.yml"
DRAIN_SCRIPT: str = "perf/wait-for-drain.sh"


def test_the_cpu_model_and_memory_come_from_proc(tmp_path: Path) -> None:
    cpu_info = tmp_path / "cpuinfo"
    cpu_info.write_text(
        "processor\t: 0\nvendor_id\t: AuthenticAMD\n"
        "model name\t: AMD EPYC 7763 64-Core Processor\nprocessor\t: 1\n"
    )
    memory_info = tmp_path / "meminfo"
    memory_info.write_text("MemTotal:       16374836 kB\nMemFree:  1 kB\n")

    assert cpu_model(cpu_info) == "AMD EPYC 7763 64-Core Processor"
    assert memory_gib(memory_info) == "15.6 GiB"
    assert cpu_model(tmp_path / "missing") == "unknown"
    assert memory_gib(tmp_path / "missing") == "unknown"


def test_the_report_gives_the_dataset_and_the_seed_time(tmp_path: Path) -> None:
    report = tmp_path / "latest.json"
    report.write_text(
        json.dumps(
            {
                "scale": {"name": "full", "businesses": 500, "messages": 2_000_000},
                "seed_seconds": 6302.4,
                "results": {},
            }
        )
    )
    unreadable = tmp_path / "broken.json"
    unreadable.write_text("{not json")

    assert read_report(report) == ("full, 500 businesses, 2,000,000 messages", 6302.4)
    assert read_report(unreadable) == (None, None)
    assert read_report(tmp_path / "missing.json") == (None, None)


def test_the_summary_is_a_markdown_table() -> None:
    table = render(4, "AMD EPYC 7763", "15.6 GiB", "medium", 161.6)

    assert table.splitlines()[2:5] == [
        "| CPUs | CPU model | Memory | Dataset | Seeding |",
        "| --- | --- | --- | --- | --- |",
        "| 4 | AMD EPYC 7763 | 15.6 GiB | medium | 162 s |",
    ]
    assert "| unknown | x | y | unknown | unknown |" in render(
        None, "x", "y", None, None
    )


def test_a_missing_report_still_shows_the_runner(tmp_path: Path) -> None:
    output = io.StringIO()

    code = main(["--report", str(tmp_path / "missing.json")], output)

    assert code == 0
    assert "### Runner" in output.getvalue()


def workflow_steps(job: str) -> list[dict[str, Any]]:
    workflow = cast(dict[str, Any], yaml.safe_load(PERF_WORKFLOW.read_text()))
    return cast(list[dict[str, Any]], workflow["jobs"][job]["steps"])


def test_both_perf_jobs_write_the_runner_into_their_summary() -> None:
    for job in ("budgets", "load"):
        runs = [str(step.get("run", "")) for step in workflow_steps(job)]
        assert any("scripts.perf_runner" in run for run in runs), job


def test_the_queue_drains_before_every_load_scenario() -> None:
    steps = workflow_steps("load")
    scenario_indexes = [
        index
        for index, step in enumerate(steps)
        if "k6 run" in str(step.get("run", ""))
    ]

    assert len(scenario_indexes) == 3
    for index in scenario_indexes:
        assert DRAIN_SCRIPT in str(steps[index - 1].get("run", ""))
    assert (PROJECT_ROOT / DRAIN_SCRIPT).stat().st_mode & 0o111
