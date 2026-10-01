import threading
from contextlib import AbstractContextManager

from app.contracts.operations import BusinessLockRegistryContract
from app.schemas.typings.businesses.prefixed_id import BusinessId


class BusinessLockRegistry(BusinessLockRegistryContract):
    """
    One lock per business, created on first use and kept for the process.

    Serializes availability re-checks and booking writes of a business so two
    customers cannot take the last unit at the same moment. It protects one
    process only; a multi-process deployment also needs a database-level
    guard (row lock or advisory lock) around the same section.
    """

    def __init__(self) -> None:
        self._locks: dict[BusinessId, threading.Lock] = {}
        self._registry_lock: threading.Lock = threading.Lock()

    def lock_for(self, business_id: BusinessId) -> AbstractContextManager[object]:
        with self._registry_lock:
            business_lock: threading.Lock | None = self._locks.get(business_id)
            if business_lock is None:
                business_lock = threading.Lock()
                self._locks[business_id] = business_lock

        return business_lock
