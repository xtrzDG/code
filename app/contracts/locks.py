"""Locks that hold across every process of the deployment (API and worker)."""

from contextlib import AbstractContextManager
from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey


class AdvisoryLockAdapterContract(AdapterContract, Protocol):
    """
    Named locks that every process sharing the storage respects; in memory
    they hold within the process. Re-entrant: the thread that holds a key
    may take it again inside the block.
    """

    def hold_with_transaction(
        self,
        key: AdvisoryLockKey,
        wait: LockWaitSeconds,
    ) -> AbstractContextManager[None]:
        """
        Hold `key` for a short block that reads and writes storage: the
        block runs in one storage transaction (a unit of work), and the lock
        ends when that transaction commits, so the next holder sees every
        write of the block. Keep the block short and free of network calls.

        Raises:
            ExternalServiceError: the lock was not free within `wait`.
        """
        raise NotImplementedError

    def hold_with_session(
        self,
        key: AdvisoryLockKey,
        wait: LockWaitSeconds,
    ) -> AbstractContextManager[None]:
        """
        Hold `key` for a long block (one that calls a language model): the
        lock is held by a connection kept for the block, while every storage
        operation of the block commits on its own. It ends with the block,
        or when the process dies.

        Raises:
            ExternalServiceError: the lock was not free within `wait`.
        """
        raise NotImplementedError
