"""
The machine beside the perf numbers in the job summary of the weekly perf
run (.github/workflows/perf.yml): how many CPUs the runner had, which
ones, its memory, and how long seeding took. A shared runner can be several
times slower than the last one (docs/operations/capacity.md, "The weekly
run of 2026-10-12"); next to these lines a slow runner shows as one.

    uv run python -m scripts.perf_runner --report perf/results/latest.json
    python3 -m scripts.perf_runner --seed-seconds 412 --dataset "50 businesses"

The latency budgets' report (PERF_REPORT) gives the dataset and the seed
time; the load job passes the seed time it measured. Standard library only
(the load job has no project environment). Prints Markdown; exit code 0
also when the report is missing or unreadable (the budgets step failed
before writing it): the runner line is shown all the same.
"""

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

CPU_INFO: Path = Path("/proc/cpuinfo")
MEMORY_INFO: Path = Path("/proc/meminfo")
UNKNOWN: str = "unknown"
KIB_PER_GIB: int = 1024 * 1024


def cpu_model(cpu_info: Path = CPU_INFO) -> str:
    """The first `model name` of /proc/cpuinfo (unknown elsewhere)."""

    try:
        lines: list[str] = cpu_info.read_text(encoding="utf-8").splitlines()
    except OSError:
        return UNKNOWN

    for line in lines:
        key, _, value = line.partition(":")
        if key.strip() == "model name" and value.strip():
            return value.strip()

    return UNKNOWN


def memory_gib(memory_info: Path = MEMORY_INFO) -> str:
    """MemTotal of /proc/meminfo in GiB (unknown elsewhere)."""

    try:
        lines: list[str] = memory_info.read_text(encoding="utf-8").splitlines()
    except OSError:
        return UNKNOWN

    for line in lines:
        key, _, value = line.partition(":")
        fields: list[str] = value.split()
        if key == "MemTotal" and fields and fields[0].isdigit():
            return f"{int(fields[0]) / KIB_PER_GIB:.1f} GiB"

    return UNKNOWN


def read_report(path: Path) -> tuple[str | None, float | None]:
    """The dataset and the seed seconds of a perf report (None: unknown)."""

    try:
        document: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None, None

    if not isinstance(document, dict):
        return None, None

    scale: object = document.get("scale")
    seconds: object = document.get("seed_seconds")
    return (
        describe_scale(scale) if isinstance(scale, dict) else None,
        float(seconds) if isinstance(seconds, int | float) else None,
    )


def describe_scale(scale: dict[object, object]) -> str:
    parts: list[str] = [str(scale.get("name", UNKNOWN))]
    for key, label in (("businesses", "businesses"), ("messages", "messages")):
        value: object = scale.get(key)
        if isinstance(value, int):
            parts.append(f"{value:,} {label}")
    return ", ".join(parts)


def render(
    cpus: int | None,
    model: str,
    memory: str,
    dataset: str | None,
    seed_seconds: float | None,
) -> str:
    seeding: str = UNKNOWN if seed_seconds is None else f"{seed_seconds:,.0f} s"
    return "\n".join(
        (
            "### Runner",
            "",
            "| CPUs | CPU model | Memory | Dataset | Seeding |",
            "| --- | --- | --- | --- | --- |",
            f"| {cpus if cpus is not None else UNKNOWN} | {model} | {memory} "
            f"| {dataset or UNKNOWN} | {seeding} |",
            "",
        )
    )


def main(arguments: Sequence[str] | None = None, output: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--report", type=Path, help="the latency budgets' report")
    parser.add_argument("--seed-seconds", type=float, help="seeding took this long")
    parser.add_argument("--dataset", help="what was seeded (without a report)")
    parsed: argparse.Namespace = parser.parse_args(arguments)
    dataset: str | None = parsed.dataset
    seed_seconds: float | None = parsed.seed_seconds
    if parsed.report is not None:
        reported_dataset, reported_seconds = read_report(parsed.report)
        dataset = dataset or reported_dataset
        seed_seconds = seed_seconds if seed_seconds is not None else reported_seconds

    print(
        render(os.cpu_count(), cpu_model(), memory_gib(), dataset, seed_seconds),
        file=sys.stdout if output is None else output,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
