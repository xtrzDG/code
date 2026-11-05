"""
The runner tries a migration file again when its locks timed out, with a
growing jittered pause, and gives up after the attempt limit.
"""

import pytest

from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.storage.constrained_integers import MigrationAttemptNumber
from app.utilities.storage.migration_retry_pause import JitteredMigrationRetryPause
from tests.storage.migration_fakes import (
    FakeMigrationSource,
    FakeMigrationStore,
    build_script,
    run,
)
from tests.storage.storage_testing import RecordedRetryPause


def test_a_file_whose_locks_timed_out_is_tried_again_after_a_pause() -> None:
    store = FakeMigrationStore(lock_timeouts={"0002_busy_table": 2})
    pause = RecordedRetryPause()

    report = run(
        FakeMigrationSource(
            [build_script("0001_first"), build_script("0002_busy_table")]
        ),
        store,
        retry_pause=pause,
    )

    assert report.newly_applied == ["0001_first", "0002_busy_table"]
    assert store.tries == [
        "0001_first",
        "0002_busy_table",
        "0002_busy_table",
        "0002_busy_table",
    ]
    assert pause.attempts == [1, 2]


def test_the_runner_gives_up_after_the_attempt_limit() -> None:
    store = FakeMigrationStore(lock_timeouts={"0001_busy_table": 9})
    pause = RecordedRetryPause()

    with pytest.raises(ExternalServiceError, match="gave up after 3 tries"):
        run(
            FakeMigrationSource([build_script("0001_busy_table")]),
            store,
            retry_pause=pause,
            attempt_limit=3,
        )

    assert store.tries == ["0001_busy_table"] * 3
    assert pause.attempts == [1, 2]
    assert store.applied == {}


def test_a_single_attempt_never_pauses() -> None:
    store = FakeMigrationStore(lock_timeouts={"0001_busy_table": 1})
    pause = RecordedRetryPause()

    with pytest.raises(ExternalServiceError):
        run(
            FakeMigrationSource([build_script("0001_busy_table")]),
            store,
            retry_pause=pause,
            attempt_limit=1,
        )

    assert pause.attempts == []


def test_pauses_grow_with_equal_jitter_up_to_the_longest() -> None:
    slept: list[float] = []
    lowest = JitteredMigrationRetryPause(
        first_seconds=1.0,
        longest_seconds=6.0,
        sleep=slept.append,
        random_fraction=lambda: 0.0,
    )
    highest = JitteredMigrationRetryPause(
        first_seconds=1.0,
        longest_seconds=6.0,
        sleep=slept.append,
        random_fraction=lambda: 1.0,
    )

    for attempt in (1, 2, 3, 4):
        lowest.pause(MigrationAttemptNumber(attempt))
    for attempt in (1, 2, 3, 4):
        highest.pause(MigrationAttemptNumber(attempt))

    assert slept == [0.5, 1.0, 2.0, 3.0, 1.0, 2.0, 4.0, 6.0]


def test_the_default_pause_is_random_but_bounded() -> None:
    slept: list[float] = []
    pause = JitteredMigrationRetryPause(sleep=slept.append)

    for _ in range(20):
        pause.pause(MigrationAttemptNumber(3))

    assert all(2.0 <= seconds <= 4.0 for seconds in slept)
    assert len(set(slept)) > 1
