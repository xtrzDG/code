"""
How one process spends its database connections and threads beyond the
pool's size (runtime section): idle connections closing, the worker's
safety-net poll of customer messages, and the owner test chat's own
limit. docs/operations/capacity.md explains the budget.
"""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.typings.platform.constrained_integers import (
    DatabaseIdleSeconds,
    DatabasePoolMinSize,
    TestChatConcurrencyLimit,
    WorkerLanePollSeconds,
)
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    parse_setting,
    read_integer,
)

# A connection unused this long is closed (the pool keeps DB_POOL_MIN_SIZE).
DEFAULT_DB_POOL_MAX_IDLE_SECONDS: int = 300
DEFAULT_DB_POOL_MIN_SIZE: int = 2
# Customer messages reach the worker through NOTIFY within milliseconds; a
# lost notification is found by this poll.
DEFAULT_WORKER_INBOUND_POLL_SECONDS: int = 2
DEFAULT_TEST_CHAT_MAX_CONCURRENCY: int = 4


class CapacitySettingsSection(TypedDict):
    """The `AppSettings` fields of connection and thread budgets."""

    db_pool_min_size: DatabasePoolMinSize
    db_pool_max_idle_seconds: DatabaseIdleSeconds
    worker_inbound_poll_seconds: WorkerLanePollSeconds
    test_chat_max_concurrency: TestChatConcurrencyLimit


def read_capacity_settings(
    environment_variables: Mapping[str, str],
) -> CapacitySettingsSection:
    return CapacitySettingsSection(
        db_pool_min_size=parse_setting(
            "DB_POOL_MIN_SIZE",
            read_integer(
                environment_variables, "DB_POOL_MIN_SIZE", DEFAULT_DB_POOL_MIN_SIZE
            ),
            DatabasePoolMinSize,
        ),
        db_pool_max_idle_seconds=parse_setting(
            "DB_POOL_MAX_IDLE_SECONDS",
            read_integer(
                environment_variables,
                "DB_POOL_MAX_IDLE_SECONDS",
                DEFAULT_DB_POOL_MAX_IDLE_SECONDS,
            ),
            DatabaseIdleSeconds,
        ),
        worker_inbound_poll_seconds=parse_setting(
            "WORKER_INBOUND_POLL_SECONDS",
            read_integer(
                environment_variables,
                "WORKER_INBOUND_POLL_SECONDS",
                DEFAULT_WORKER_INBOUND_POLL_SECONDS,
            ),
            WorkerLanePollSeconds,
        ),
        test_chat_max_concurrency=parse_setting(
            "TEST_CHAT_MAX_CONCURRENCY",
            read_integer(
                environment_variables,
                "TEST_CHAT_MAX_CONCURRENCY",
                DEFAULT_TEST_CHAT_MAX_CONCURRENCY,
            ),
            TestChatConcurrencyLimit,
        ),
    )
