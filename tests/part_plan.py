"""
Which test files a CI part runs (TEST_PART="2/4", tests/conftest.py).

CI runs the backend tests in two groups, the tests on Postgres and the rest
(`-m postgres` and `-m "not postgres"`), and each group in parts on machines
of their own whose coverage is combined (.github/workflows/ci.yml). A part
keeps the test files the plan gives it: each file of the group weighs the
seconds its tests of that group took in the last measured run
(tests/durations.json), a file not measured yet the mean of the measured
ones, and files go, longest first, to the part with the least work so far.
The plan is a pure function of the collected files and the durations, so
every part (and every xdist worker of a part) computes the same one.

`uv run python -m scripts.backend_test_durations` measures the suite again
(docs/operations/ci.md).
"""

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

DURATIONS_PATH: Path = Path(__file__).with_name("durations.json")
POSTGRES_GROUP: str = "postgres"
REST_GROUP: str = "rest"
GROUPS: tuple[str, ...] = (POSTGRES_GROUP, REST_GROUP)
# The user property that carries a test's group to its report.
GROUP_PROPERTY: str = "test_group"
# The weight of every file while nothing of its group is measured.
UNMEASURED_SECONDS: float = 1.0
PART_PATTERN: re.Pattern[str] = re.compile(r"^(\d+)/(\d+)$")


@dataclass(frozen=True)
class Part:
    """Part `index` (from 1) of `total`."""

    index: int
    total: int


@dataclass(frozen=True)
class TestFile:
    """A test file's tests of one group, with the seconds they weigh."""

    __test__ = False

    group: str
    path: str
    seconds: float
    measured: bool


def parse_part(value: str | None) -> Part | None:
    """'2/4' → Part(2, 4); nothing → every test (local runs)."""
    if not value:
        return None
    match = PART_PATTERN.match(value.strip())
    if match is None or not 1 <= int(match.group(1)) <= int(match.group(2)):
        raise ValueError(f'TEST_PART must look like "2/4" (part 1..total), not "{value}".')
    return Part(index=int(match.group(1)), total=int(match.group(2)))


def load_durations(path: Path = DURATIONS_PATH) -> dict[str, dict[str, float]]:
    """Seconds per test file, by group; nothing measured without the file."""
    if not path.exists():
        return {group: {} for group in GROUPS}
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != set(GROUPS):
        raise ValueError(f"{path} must have exactly the groups {', '.join(GROUPS)}.")
    durations: dict[str, dict[str, float]] = {}
    for group, files in raw.items():
        if not isinstance(files, dict):
            raise ValueError(f"{path}: {group} must map test files to seconds.")
        durations[str(group)] = {}
        for name, seconds in files.items():
            if not isinstance(seconds, int | float) or isinstance(seconds, bool) or seconds < 0:
                raise ValueError(f"{path}: {group} {name} must be a number of seconds.")
            durations[str(group)][str(name)] = float(seconds)
    return durations


def weigh_files(
    files: Iterable[tuple[str, str]], durations: Mapping[str, Mapping[str, float]]
) -> list[TestFile]:
    """Each (group, path) with its measured seconds or its group's mean."""
    keys: list[tuple[str, str]] = sorted(set(files))
    weighed: list[TestFile] = []
    for group in sorted({group for group, _ in keys}):
        measured_seconds: Mapping[str, float] = durations.get(group, {})
        paths: list[str] = [path for key_group, path in keys if key_group == group]
        known: list[float] = [measured_seconds[path] for path in paths if path in measured_seconds]
        mean: float = sum(known) / len(known) if known else UNMEASURED_SECONDS
        weighed.extend(
            TestFile(group, path, measured_seconds[path], True)
            if path in measured_seconds
            else TestFile(group, path, mean, False)
            for path in paths
        )
    return weighed


def plan_parts(files: Iterable[TestFile], total: int) -> list[list[TestFile]]:
    """Every part's files, longest first to the part with the least work."""
    parts: list[list[TestFile]] = [[] for _ in range(total)]
    loads: list[float] = [0.0] * total
    for test_file in sorted(files, key=lambda item: (-item.seconds, item.group, item.path)):
        lightest: int = min(range(total), key=lambda index: (loads[index], index))
        parts[lightest].append(test_file)
        loads[lightest] += test_file.seconds
    return [sorted(part, key=lambda item: (item.group, item.path)) for part in parts]


def files_of_part(files: Iterable[TestFile], part: Part) -> set[tuple[str, str]]:
    """The (group, path) pairs the given part runs."""
    return {(item.group, item.path) for item in plan_parts(files, part.total)[part.index - 1]}
