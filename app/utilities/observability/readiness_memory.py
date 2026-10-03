"""What GET /readyz of one process remembers between its probes."""

import threading

from typed_time_provider import Microseconds

from app.contracts.health import ReadinessMemoryContract


class ReadinessMemory(ReadinessMemoryContract):
    """
    Thread-safe (readiness checks run on two threads of their own). One per
    process: the pool and the migrations it remembers are this process's.
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._exhausted_since: Microseconds | None = None
        self._are_migrations_applied: bool | None = None

    def note_pool(self, is_exhausted: bool, now: Microseconds) -> Microseconds | None:
        with self._lock:
            if not is_exhausted:
                self._exhausted_since = None
            elif self._exhausted_since is None:
                self._exhausted_since = now

            return self._exhausted_since

    def note_migrations(self, are_applied: bool) -> None:
        with self._lock:
            self._are_migrations_applied = are_applied

    def were_migrations_applied(self) -> bool | None:
        with self._lock:
            return self._are_migrations_applied
