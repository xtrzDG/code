from collections.abc import Generator
from contextlib import contextmanager

from app.adapters.locks.process_locks import ProcessLocks
from app.contracts.locks import AdvisoryLockAdapterContract
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey


class InMemoryAdvisoryLockAdapter(AdvisoryLockAdapterContract):
    """
    Named locks of this process: tests and development without a database,
    where every document lives in this process anyway. A transaction-held
    and a session-held lock are the same here (in-memory storage writes
    are visible at once).
    """

    def __init__(self, process_locks: ProcessLocks | None = None) -> None:
        self._process_locks: ProcessLocks = (
            ProcessLocks() if process_locks is None else process_locks
        )

    @contextmanager
    def hold_with_transaction(
        self,
        key: AdvisoryLockKey,
        wait: LockWaitSeconds,
    ) -> Generator[None]:
        with self._process_locks.held(key, float(int(wait))):
            yield

    @contextmanager
    def hold_with_session(
        self,
        key: AdvisoryLockKey,
        wait: LockWaitSeconds,
    ) -> Generator[None]:
        with self._process_locks.held(key, float(int(wait))):
            yield
