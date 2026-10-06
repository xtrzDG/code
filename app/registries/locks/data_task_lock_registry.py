from contextlib import AbstractContextManager

from app.contracts.data_tasks import DataTaskLockRegistryContract
from app.contracts.locks import AdvisoryLockAdapterContract
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey

DATA_TASK_LOCK_KEY: AdvisoryLockKey = AdvisoryLockKey("post-deploy-data-tasks")
# A runner that finds the lock taken skips its turn: another worker runs
# the tasks, and the next period looks again.
DATA_TASK_LOCK_WAIT: LockWaitSeconds = LockWaitSeconds(1)


class DataTaskLockRegistry(DataTaskLockRegistryContract):
    """
    One lock for the whole data-task run, held by a connection of its own
    for the run (`hold_with_session`: each batch commits by itself) and
    released when the run ends or its process dies.
    """

    def __init__(self, advisory_locks: AdvisoryLockAdapterContract) -> None:
        self._advisory_locks: AdvisoryLockAdapterContract = advisory_locks

    def lock_runner(self) -> AbstractContextManager[object]:
        return self._advisory_locks.hold_with_session(
            DATA_TASK_LOCK_KEY, DATA_TASK_LOCK_WAIT
        )
