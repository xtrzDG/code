"""One runner at a time; a new schema version makes a migration due again."""

from concurrent.futures import Future, ThreadPoolExecutor

from typed_time_provider import Microseconds

from app.adapters.locks.in_memory_advisory_lock_adapter import (
    InMemoryAdvisoryLockAdapter,
)
from app.adapters.locks.process_locks import ProcessLocks
from app.schemas.constants.maintenance import DataTaskKind, DataTaskStatus
from app.schemas.dto.data_tasks import DataTaskDefinition
from app.schemas.dto.jobs import JobReport
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.maintenance.constrained_strings import DataTaskKey
from app.schemas.typings.storage.constrained_integers import (
    DocumentSchemaVersionNumber,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.maintenance.data_task_progress import (
    ERROR_TEXT_LIMIT,
    after_failed_batch,
    new_state,
)
from tests.data_tasks.data_task_support import (
    NOW,
    backfill_of,
    registry_of,
)
from tests.data_tasks.runner_world import RunnerWorld, pause_inside_a_batch

SEEN: str = "backfill_lookup:contacts.last_seen_at"
CONTACTS: str = "migrate_documents:contacts"


class VersionedRegistry:
    """A registry whose contacts migration targets `version`."""

    def __init__(self, version: int) -> None:
        self.version: int = version

    def list_tasks(self) -> list[DataTaskDefinition]:
        return [
            DataTaskDefinition(
                key=DataTaskKey(CONTACTS),
                kind=DataTaskKind.MIGRATE_DOCUMENTS,
                collection_name=DocumentCollectionName("contacts"),
                target_version=DocumentSchemaVersionNumber(self.version),
            )
        ]

    def find_task(self, key: DataTaskKey) -> DataTaskDefinition | None:
        return next((task for task in self.list_tasks() if task.key == key), None)

    def tasks_for_list(self, indexed_list: object) -> list[DataTaskDefinition]:
        del indexed_list
        return []


def test_a_second_runner_skips_its_turn_while_the_first_holds_the_lock() -> None:
    shared = ProcessLocks()
    registry = registry_of(backfills=[backfill_of("contacts", "last_seen_at")])
    first = RunnerWorld(registry, locks=InMemoryAdvisoryLockAdapter(shared))
    second = RunnerWorld(
        registry, locks=InMemoryAdvisoryLockAdapter(shared), states=first.states
    )
    first.batches.rows[SEEN] = 10
    second.batches.rows[SEEN] = 10
    inside, release = pause_inside_a_batch(first.batches)

    with ThreadPoolExecutor(max_workers=1) as pool:
        running: Future[JobReport] = pool.submit(first.run)
        assert inside.wait(timeout=10)

        skipped: JobReport = second.run()
        release.set()
        finished: JobReport = running.result(timeout=10)

    assert int(skipped.processed_count) == 0
    assert second.batches.requests == []
    assert int(finished.processed_count) == 10
    assert first.state(SEEN).status is DataTaskStatus.DONE


def test_the_lock_is_free_again_after_a_run() -> None:
    shared = ProcessLocks()
    registry = registry_of(backfills=[backfill_of("contacts", "last_seen_at")])
    runner = RunnerWorld(registry, locks=InMemoryAdvisoryLockAdapter(shared))
    runner.batches.rows[SEEN] = 3
    runner.batches.fail_next = 1

    runner.run()
    runner.run()

    assert runner.state(SEEN).status is DataTaskStatus.DONE


def test_a_new_collection_version_makes_a_done_migration_due_again() -> None:
    registry = VersionedRegistry(version=4)
    runner = RunnerWorld(registry)
    runner.batches.rows[CONTACTS] = 20

    runner.run()
    assert runner.state(CONTACTS).status is DataTaskStatus.DONE

    registry.version = 5
    runner.clock.now += 1_000_000
    deployed_at: int = runner.clock.now

    report = runner.run()

    state = runner.state(CONTACTS)
    assert int(report.processed_count) == 20
    assert state.status is DataTaskStatus.DONE
    assert state.target_version == DocumentSchemaVersionNumber(5)
    assert int(state.scanned_count) == 20, "The new walk counts from zero."
    assert int(state.pending_since) == deployed_at


def test_a_batch_error_keeps_a_short_text_and_the_walk_where_it_was() -> None:
    task = registry_of(backfills=[backfill_of("contacts", "last_seen_at")])
    state = new_state(task.list_tasks()[0], Microseconds(NOW))

    failed = after_failed_batch(
        state, ExternalServiceError("x" * 900), Microseconds(NOW), None
    )

    assert failed.status is DataTaskStatus.PENDING
    assert len(str(failed.last_error)) == ERROR_TEXT_LIMIT
    assert failed.position is None
    assert int(failed.failure_count) == 1
    assert failed.started_at == NOW
