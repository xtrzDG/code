"""Marks the tests that reach a throwaway Postgres server; keeps a CI part's files.

CI runs them in jobs of their own (`pytest -m postgres`) next to the rest
(`pytest -m "not postgres"`) and combines the coverage files of every job
(.github/workflows/ci.yml). A test runs on Postgres when its fixtures reach
`postgres_server`, or when a fixture parametrized over the storages picked
its "postgres" variant (which reaches the server through
`request.getfixturevalue`, out of sight of the fixture closure).

Each group runs in parts: with TEST_PART="2/4" a run keeps only the test
files that tests/part_plan.py gives part 2 of 4, after `-m` chose the group.
With TEST_DURATIONS_REPORT=<file> it writes how long each file took
(tests/duration_recorder.py).
"""

import os
from collections.abc import Generator
from pathlib import Path

import pytest

from tests.duration_recorder import DurationRecorder
from tests.part_plan import (
    GROUP_PROPERTY,
    POSTGRES_GROUP,
    REST_GROUP,
    files_of_part,
    load_durations,
    parse_part,
    weigh_files,
)

POSTGRES_MARK: str = "postgres"
POSTGRES_FIXTURE: str = "postgres_server"
POSTGRES_PARAMETER_VALUE: str = "postgres"
TEST_PART_VARIABLE: str = "TEST_PART"
DURATIONS_REPORT_VARIABLE: str = "TEST_DURATIONS_REPORT"


def runs_on_postgres(item: pytest.Item) -> bool:
    if not isinstance(item, pytest.Function):
        return False
    if POSTGRES_FIXTURE in item.fixturenames:
        return True
    if not hasattr(item, "callspec"):
        return False
    return POSTGRES_PARAMETER_VALUE in item.callspec.params.values()


def group_and_file(item: pytest.Item) -> tuple[str, str]:
    group: str = (
        POSTGRES_GROUP if item.get_closest_marker(POSTGRES_MARK) else REST_GROUP
    )
    return group, item.nodeid.split("::", 1)[0]


def pytest_configure(config: pytest.Config) -> None:
    report_path: str = os.environ.get(DURATIONS_REPORT_VARIABLE, "")
    # Under xdist only the controller sees every report; workers have `workerinput`.
    if report_path and not hasattr(config, "workerinput"):
        config.pluginmanager.register(
            DurationRecorder(Path(report_path)), "duration-recorder"
        )


@pytest.hookimpl(wrapper=True)
def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> Generator[None]:
    # Before `-m` selects: mark the tests on Postgres and name each test's group.
    for item in items:
        if runs_on_postgres(item):
            item.add_marker(POSTGRES_MARK)
        item.user_properties.append((GROUP_PROPERTY, group_and_file(item)[0]))

    yield

    # After `-m` selected the group: keep this part's files.
    part = parse_part(os.environ.get(TEST_PART_VARIABLE))
    if part is None:
        return
    weighed = weigh_files((group_and_file(item) for item in items), load_durations())
    kept_files: set[tuple[str, str]] = files_of_part(weighed, part)
    kept: list[pytest.Item] = [
        item for item in items if group_and_file(item) in kept_files
    ]
    deselected: list[pytest.Item] = [
        item for item in items if group_and_file(item) not in kept_files
    ]
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = kept
