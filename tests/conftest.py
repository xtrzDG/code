"""Marks the tests that run against a throwaway Postgres server.

CI runs them in a job of their own (`pytest -m postgres`) next to the rest
(`pytest -m "not postgres"`) and combines both coverage files
(.github/workflows/ci.yml). A test runs on Postgres when its fixtures reach
`postgres_server`, or when a fixture parametrized over the storages picked
its "postgres" variant (which reaches the server through
`request.getfixturevalue`, out of sight of the fixture closure).
"""

import pytest

POSTGRES_MARK: str = "postgres"
POSTGRES_FIXTURE: str = "postgres_server"
POSTGRES_PARAMETER_VALUE: str = "postgres"


def runs_on_postgres(item: pytest.Item) -> bool:
    if not isinstance(item, pytest.Function):
        return False
    if POSTGRES_FIXTURE in item.fixturenames:
        return True
    if not hasattr(item, "callspec"):
        return False
    return POSTGRES_PARAMETER_VALUE in item.callspec.params.values()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if runs_on_postgres(item):
            item.add_marker(POSTGRES_MARK)
