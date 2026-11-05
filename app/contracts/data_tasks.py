"""
Post-deploy data tasks (docs/operations/deploys.md): the registry of what
to rewrite or fill after a release, the tasks' stored progress, one keyset
batch on the storage, the lock that keeps one runner at a time, and the
worker pulses that tell whether the release overlap is over.
"""

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.adapter_contract import AdapterContract
from app.contracts.registry_contract import RegistryContract
from app.contracts.repo_contract import RepoContract
from app.schemas.constants.maintenance import IndexedList
from app.schemas.domain.data_tasks import DataTaskStateDocument
from app.schemas.domain.jobs import WorkerHeartbeatDocument
from app.schemas.dto.data_tasks import (
    DataTaskBatchRequest,
    DataTaskBatchResult,
    DataTaskDefinition,
)
from app.schemas.typings.maintenance.constrained_strings import DataTaskKey


class DataTaskRegistryContract(RegistryContract, Protocol):
    """
    Every post-deploy data task of this release, in the order they run:
    document migrations first (a migrated row runs the lookup trigger, so
    it needs no backfill afterwards), then lookup backfills.
    """

    def list_tasks(self) -> list[DataTaskDefinition]:
        raise NotImplementedError

    def find_task(self, key: DataTaskKey) -> DataTaskDefinition | None:
        raise NotImplementedError

    def tasks_for_list(self, indexed_list: IndexedList) -> list[DataTaskDefinition]:
        """The tasks that fill what the list pages by."""
        raise NotImplementedError


class DataTaskStateRepoContract(RepoContract, Protocol):
    """The stored progress of the data tasks, one document per task key."""

    def get_many(self, keys: Sequence[DataTaskKey]) -> list[DataTaskStateDocument]:
        raise NotImplementedError

    def save(self, state: DataTaskStateDocument) -> None:
        raise NotImplementedError

    def modify(
        self,
        key: DataTaskKey,
        change: Callable[[DataTaskStateDocument], DataTaskStateDocument | None],
    ) -> DataTaskStateDocument | None:
        """
        Read a task's state, let `change` turn it into the state to store and
        write that in one step (no other write can come in between). None,
        and nothing written, when there is no state or `change` returns
        None; an error raised by `change` leaves the state as it was.
        """
        raise NotImplementedError


class DataTaskBatchAdapterContract(AdapterContract, Protocol):
    """
    One keyset batch of a data task on the storage, platform-wide (every
    business), in a short transaction of its own whose lock waits are
    bounded, so the live application is never queued behind it.
    """

    def run_batch(self, request: DataTaskBatchRequest) -> DataTaskBatchResult:
        """
        Look at the next `batch_size` rows after `after` and rewrite the
        outdated documents (a migration) or fill the empty column (a
        backfill). Idempotent: a row is changed only when it still needs it.

        Raises:
            MigrationLockTimeoutError: a row stayed locked by another
                transaction for too long (nothing of the batch was written).
            ExternalServiceError: the storage failed.
        """
        raise NotImplementedError


class DataTaskLockRegistryContract(RegistryContract, Protocol):
    def lock_runner(self) -> AbstractContextManager[object]:
        """
        Held while one process runs the data tasks, so two workers never
        walk the same table at once.

        Raises:
            ExternalServiceError: another process holds it.
        """
        raise NotImplementedError


class WorkerPulseRepoContract(RepoContract, Protocol):
    def list_pulses_since(self, since: Microseconds) -> list[WorkerHeartbeatDocument]:
        """Pulses of worker processes that beat at or after `since`."""
        raise NotImplementedError
