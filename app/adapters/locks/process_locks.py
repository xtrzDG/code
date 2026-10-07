"""Named re-entrant locks of one process, created on demand and forgotten unused."""

import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey

KEY_PURPOSE_SEPARATOR: str = "|"


@dataclass
class _NamedLock:
    lock: threading.RLock
    users: int


class ProcessLocks:
    """
    One re-entrant lock per key while anybody holds it or waits for it; the
    lock of a key nobody uses any more is dropped, so memory stays bounded
    however many customers and businesses come and go. Distinct keys never
    share a lock, so nested locks of different keys cannot deadlock on a
    shared stripe.
    """

    def __init__(self) -> None:
        self._locks: dict[AdvisoryLockKey, _NamedLock] = {}
        self._guard: threading.Lock = threading.Lock()

    @contextmanager
    def held(self, key: AdvisoryLockKey, wait_seconds: float) -> Generator[None]:
        """
        Hold the key's lock for the block, waiting at most `wait_seconds`.

        Raises:
            ExternalServiceError: the lock was not free in time.
        """

        named_lock: _NamedLock = self._join(key)
        try:
            if not named_lock.lock.acquire(timeout=max(0.0, wait_seconds)):
                raise lock_wait_exceeded(key, wait_seconds)

            try:
                yield
            finally:
                named_lock.lock.release()
        finally:
            self._leave(key, named_lock)

    def _join(self, key: AdvisoryLockKey) -> _NamedLock:
        with self._guard:
            named_lock: _NamedLock | None = self._locks.get(key)
            if named_lock is None:
                named_lock = _NamedLock(lock=threading.RLock(), users=0)
                self._locks[key] = named_lock

            named_lock.users += 1
            return named_lock

    def _leave(self, key: AdvisoryLockKey, named_lock: _NamedLock) -> None:
        with self._guard:
            named_lock.users -= 1
            if named_lock.users == 0:
                del self._locks[key]


def describe_lock_purpose(key: AdvisoryLockKey) -> str:
    """The purpose part of a key ("bookings"), without the ids it names."""

    return str(key).split(KEY_PURPOSE_SEPARATOR, 1)[0]


def lock_wait_exceeded(
    key: AdvisoryLockKey,
    wait_seconds: float,
) -> ExternalServiceError:
    """The error of a lock that stayed busy; it names no customer or business."""

    return ExternalServiceError(
        f"The {describe_lock_purpose(key)} lock stayed busy for "
        f"{wait_seconds:.0f} s (an earlier request still holds it); try "
        "again in a moment."
    )
