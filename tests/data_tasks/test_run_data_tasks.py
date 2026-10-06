"""The batch worker runs the post-deploy data tasks by themselves."""

from app.schemas.constants.maintenance import DataTaskStatus, IndexedList
from app.schemas.typings.maintenance.constrained_strings import DataTaskPosition
from app.schemas.typings.platform.constrained_strings import ReleaseVersion
from tests.data_tasks.data_task_support import (
    MINUTE,
    NOW,
    OLD_RELEASE,
    RELEASE,
    SECOND,
    backfill_of,
    pulse,
    registry_of,
)
from tests.data_tasks.runner_world import RunnerWorld, position_of

SEEN: str = "backfill_lookup:contacts.last_seen_at"
UPDATED: str = "backfill_lookup:knowledge_items.updated_at"


def batches_of(runner: RunnerWorld, key: str) -> list[DataTaskPosition | None]:
    """Where each batch of one task started."""

    return [
        request.after
        for request in runner.batches.requests
        if str(request.task.key) == key
    ]


def world(**options: object) -> RunnerWorld:
    registry = registry_of(
        backfills=[
            backfill_of("contacts", "last_seen_at", IndexedList.CUSTOMERS),
            backfill_of("knowledge_items", "updated_at", IndexedList.KNOWLEDGE),
        ]
    )
    return RunnerWorld(registry, **options)  # type: ignore[arg-type]


def test_tasks_wait_while_a_worker_of_the_previous_release_still_beats() -> None:
    runner = world()
    runner.batches.rows[SEEN] = 12_000
    runner.beat([pulse(RELEASE, NOW), pulse(OLD_RELEASE, NOW - 5 * MINUTE, "w-2")])

    report = runner.run()

    assert int(report.processed_count) == 0
    assert runner.batches.requests == []
    # Every task is recorded as due from now on, for the stall alert.
    assert runner.state(SEEN).status is DataTaskStatus.PENDING
    assert int(runner.state(SEEN).pending_since) == NOW
    assert runner.state(UPDATED).status is DataTaskStatus.PENDING


def test_once_the_overlap_is_over_every_task_runs_in_batches_of_5000() -> None:
    runner = world()
    runner.batches.rows[SEEN] = 12_000
    runner.batches.rows[UPDATED] = 30
    runner.beat([pulse(OLD_RELEASE, NOW - 16 * MINUTE), pulse(RELEASE, NOW)])

    report = runner.run()

    assert int(report.processed_count) == 12_030
    assert [
        (str(request.task.key), request.after, int(request.batch_size))
        for request in runner.batches.requests
    ] == [
        (SEEN, None, 5_000),
        (SEEN, position_of(4_999), 5_000),
        (SEEN, position_of(9_999), 5_000),
        (UPDATED, None, 5_000),
    ]
    seen = runner.state(SEEN)
    assert seen.status is DataTaskStatus.DONE
    assert (int(seen.scanned_count), int(seen.changed_count)) == (12_000, 12_000)
    assert int(seen.batch_count) == 3
    assert seen.position is None
    assert seen.release == RELEASE
    assert seen.finished_at is not None
    assert runner.state(UPDATED).status is DataTaskStatus.DONE

    assert int(runner.run().processed_count) == 0, "Done tasks are not walked again."
    assert len(runner.batches.requests) == 4


def test_a_run_stops_at_its_time_limit_and_the_next_goes_on_from_there() -> None:
    runner = world(run_seconds=60, batch_step=25 * SECOND)
    runner.batches.rows[SEEN] = 25_000

    runner.run()

    first = runner.state(SEEN)
    assert first.status is DataTaskStatus.RUNNING
    assert int(first.batch_count) == 3
    assert first.position == position_of(14_999)

    runner.run()

    assert batches_of(runner, SEEN)[3:] == [position_of(14_999), position_of(19_999)]
    assert runner.state(SEEN).status is DataTaskStatus.DONE
    assert int(runner.state(SEEN).scanned_count) == 25_000


def test_a_failed_batch_is_recorded_and_tried_again_on_the_next_run() -> None:
    runner = world(batch_size=100)
    runner.batches.rows[SEEN] = 150
    runner.batches.fail_next = 1

    runner.run()

    failed = runner.state(SEEN)
    assert failed.status is DataTaskStatus.PENDING
    assert int(failed.failure_count) == 1
    assert str(failed.last_error).startswith("ExternalServiceError: ")
    # The other task did not wait for it.
    assert runner.state(UPDATED).status is DataTaskStatus.DONE

    runner.run()

    done = runner.state(SEEN)
    assert done.status is DataTaskStatus.DONE
    assert int(done.failure_count) == 0
    assert done.last_error is None
    assert batches_of(runner, SEEN) == [None, None, position_of(99)]


def test_rows_a_migration_cannot_upgrade_fail_the_task_until_a_new_release() -> None:
    runner = world(batch_size=100)
    runner.batches.rows[SEEN] = 250
    runner.batches.broken = {7, 180}

    runner.run()

    failed = runner.state(SEEN)
    assert failed.status is DataTaskStatus.FAILED
    assert int(failed.failed_row_count) == 2
    assert [str(key) for key in failed.failed_document_keys] == ["doc_7", "doc_180"]
    assert int(failed.changed_count) == 248

    runner.run()
    assert len(batches_of(runner, SEEN)) == 3, "The same release does not retry."

    fixed = RunnerWorld(
        registry_of(backfills=[backfill_of("contacts", "last_seen_at")]),
        release=ReleaseVersion("release-fix"),
        batch_size=100,
        states=runner.states,
    )
    fixed.batches.rows[SEEN] = 250
    fixed.clock.now = runner.clock.now + MINUTE

    fixed.run()

    walked = fixed.state(SEEN)
    assert walked.status is DataTaskStatus.DONE
    assert int(walked.scanned_count) == 250
    assert int(walked.pending_since) == NOW, "It stays due since it first was."
    assert walked.release == ReleaseVersion("release-fix")
