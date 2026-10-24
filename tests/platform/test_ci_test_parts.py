"""
The backend tests run in CI parts balanced by measured duration.

tests/part_plan.py plans the parts, tests/conftest.py keeps a part's files
(TEST_PART) after `-m` chose the group, and the committed
tests/durations.json keeps every part of .github/workflows/ci.yml within its
budget (docs/operations/ci.md).
"""

import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from tests import conftest
from tests.part_plan import (
    GROUP_PROPERTY,
    Part,
    TestFile,
    files_of_part,
    load_durations,
    parse_part,
    plan_parts,
    weigh_files,
)

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
CI_WORKFLOW: Path = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
# A part's test step on CI: its four xdist workers share its files' seconds
# (tests/durations.json holds seconds on CI's runners), never faster than its
# longest file, plus about 30 seconds to start the workers and collect the
# suite; it should stay within four minutes (docs/operations/ci.md).
PART_WORKERS: int = 4
PART_START_SECONDS: float = 30.0
PART_BUDGET_SECONDS: float = 240.0
PERF_MODULE: re.Pattern[str] = re.compile(
    r"^pytestmark = pytest\.mark\.perf$", re.MULTILINE
)


def test_a_part_is_read_from_its_index_and_total() -> None:
    assert parse_part("2/4") is not None
    part = parse_part(" 3/4 ")
    assert part is not None and (part.index, part.total) == (3, 4)
    assert parse_part(None) is None
    assert parse_part("") is None


@pytest.mark.parametrize("value", ["0/4", "5/4", "1/0", "two/4", "1-4"])
def test_a_malformed_part_is_refused(value: str) -> None:
    with pytest.raises(ValueError, match="TEST_PART"):
        parse_part(value)


def test_an_unmeasured_file_weighs_the_mean_of_its_group() -> None:
    weighed = weigh_files(
        [
            ("rest", "tests/a.py"),
            ("rest", "tests/b.py"),
            ("rest", "tests/new.py"),
            ("postgres", "tests/new.py"),
        ],
        {
            "rest": {"tests/a.py": 10.0, "tests/b.py": 30.0},
            "postgres": {"tests/c.py": 5.0},
        },
    )

    assert weighed == [
        TestFile("postgres", "tests/new.py", 1.0, False),
        TestFile("rest", "tests/a.py", 10.0, True),
        TestFile("rest", "tests/b.py", 30.0, True),
        TestFile("rest", "tests/new.py", 20.0, False),
    ]


def test_the_longest_file_goes_first_to_the_part_with_the_least_work() -> None:
    files = [
        TestFile("rest", f"tests/{name}.py", seconds, True)
        for name, seconds in (("a", 5), ("b", 9), ("c", 4), ("d", 3), ("e", 2))
    ]

    plan = plan_parts(files, 2)

    assert [[item.path for item in part] for part in plan] == [
        ["tests/b.py", "tests/d.py"],
        ["tests/a.py", "tests/c.py", "tests/e.py"],
    ]
    assert files_of_part(files, Part(1, 2)) == {
        ("rest", "tests/b.py"),
        ("rest", "tests/d.py"),
    }


def test_every_file_goes_to_exactly_one_part_in_any_order() -> None:
    files = [
        TestFile("rest", f"tests/t{index:02d}.py", float((index * 37) % 23 + 1), True)
        for index in range(40)
    ]

    plan = plan_parts(files, 4)

    assert sorted(item.path for part in plan for item in part) == sorted(
        item.path for item in files
    )
    assert plan_parts(list(reversed(files)), 4) == plan
    loads = [sum(item.seconds for item in part) for part in plan]
    assert max(loads) - min(loads) <= 23


def test_durations_must_name_both_groups_with_seconds(tmp_path: Path) -> None:
    path = tmp_path / "durations.json"
    path.write_text('{"rest": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="exactly the groups"):
        load_durations(path)
    path.write_text(
        '{"rest": {"tests/a.py": "slow"}, "postgres": {}}', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="number of seconds"):
        load_durations(path)
    assert load_durations(tmp_path / "missing.json") == {"postgres": {}, "rest": {}}


@dataclass
class FakeItem:
    """The parts of a pytest item the collection hook reads."""

    nodeid: str
    on_postgres: bool = False
    user_properties: list[tuple[str, object]] = field(
        default_factory=list[tuple[str, object]]
    )

    def get_closest_marker(self, name: str) -> object | None:
        return object() if name == "postgres" and self.on_postgres else None

    def add_marker(self, name: str) -> None:
        self.on_postgres = self.on_postgres or name == "postgres"


def on_postgres(item: FakeItem) -> bool:
    return item.on_postgres


@dataclass
class FakeHook:
    deselected: list[FakeItem] = field(default_factory=list[FakeItem])

    def pytest_deselected(self, items: list[FakeItem]) -> None:
        self.deselected.extend(items)


@dataclass
class FakeConfig:
    hook: FakeHook = field(default_factory=FakeHook)


def run_collection_hook(items: list[FakeItem], select: list[str]) -> FakeConfig:
    """Drives the conftest's wrapper; `select` stands in for `-m` between its halves."""
    config = FakeConfig()
    hook = conftest.pytest_collection_modifyitems(cast(Any, config), cast(Any, items))
    next(hook)
    items[:] = [item for item in items if item.nodeid in select]
    with pytest.raises(StopIteration):
        next(hook)
    return config


def test_the_hook_names_each_tests_group_and_keeps_only_its_parts_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(conftest, "runs_on_postgres", on_postgres)
    monkeypatch.setattr(
        conftest,
        "load_durations",
        lambda: {"rest": {"tests/a.py": 9.0, "tests/b.py": 1.0}, "postgres": {}},
    )
    monkeypatch.setenv("TEST_PART", "2/2")
    items = [
        FakeItem("tests/a.py::one"),
        FakeItem("tests/b.py::two"),
        FakeItem("tests/b.py::three"),
        FakeItem("tests/c.py::pg", True),
    ]
    rest = ["tests/a.py::one", "tests/b.py::two", "tests/b.py::three"]

    config = run_collection_hook(items, rest)

    assert [item.nodeid for item in items] == ["tests/b.py::two", "tests/b.py::three"]
    assert [item.nodeid for item in config.hook.deselected] == ["tests/a.py::one"]
    assert all((GROUP_PROPERTY, "rest") in item.user_properties for item in items)


def test_without_a_part_the_hook_keeps_everything(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TEST_PART", raising=False)
    monkeypatch.setattr(conftest, "runs_on_postgres", on_postgres)
    items = [FakeItem("tests/a.py::one"), FakeItem("tests/b.py::two")]

    config = run_collection_hook(items, ["tests/a.py::one", "tests/b.py::two"])

    assert len(items) == 2
    assert config.hook.deselected == []


def ci_parts() -> dict[str, int]:
    """Parts per group in the CI matrix."""
    workflow = cast(
        dict[str, Any], yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    )
    include = cast(
        list[dict[str, Any]],
        workflow["jobs"]["backend-tests"]["strategy"]["matrix"]["include"],
    )
    return {str(entry["group"]): int(entry["parts"]) for entry in include}


def test_the_committed_durations_keep_every_ci_part_within_its_budget() -> None:
    durations = load_durations()

    for group, total in ci_parts().items():
        files = weigh_files(((group, path) for path in durations[group]), durations)
        estimates = [
            round(
                max(
                    sum(item.seconds for item in part) / PART_WORKERS,
                    max(item.seconds for item in part),
                )
                + PART_START_SECONDS
            )
            for part in plan_parts(files, total)
        ]
        assert max(estimates) <= PART_BUDGET_SECONDS, (
            f"{group}: parts of about {estimates} seconds on CI; add a part in "
            "ci.yml or split the slowest test files (docs/operations/ci.md)."
        )


def test_the_committed_durations_name_existing_test_files() -> None:
    durations = load_durations()
    # CI never runs the timing budgets (`-m "not perf"`), so they have no duration.
    test_files = {
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "tests").rglob("test_*.py")
        if PERF_MODULE.search(path.read_text(encoding="utf-8")) is None
    }
    measured = {path for files in durations.values() for path in files}

    assert measured, (
        "tests/durations.json is empty: measure the suite (docs/operations/ci.md)."
    )
    gone = sorted(measured - test_files)
    unmeasured = sorted(test_files - measured)
    if gone or unmeasured:
        # The plan still works (an unmeasured file weighs the mean); refresh
        # the file when the parts drift apart.
        warnings.warn(
            f"tests/durations.json: {len(unmeasured)} test files without a "
            f"duration, {len(gone)} entries of files that are gone; refresh it "
            "(docs/operations/ci.md).",
            stacklevel=1,
        )
