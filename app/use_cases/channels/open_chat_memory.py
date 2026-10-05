"""Which businesses' web chats a process recently found open."""

import threading

from typed_time_provider import Microseconds

from app.schemas.typings.businesses.prefixed_id import BusinessId

MICROSECONDS_PER_SECOND: int = 1_000_000
# How long a web chat found open is believed open without reading its
# channel again: the longest a chat switched off still answers polls.
OPEN_CHAT_MEMORY_SECONDS: int = 10


class OpenChatMemory:
    """
    The web chats a process found open, each for `OPEN_CHAT_MEMORY_SECONDS`
    from the moment it was read (thread-safe, one entry per business).
    Only open chats are remembered: a chat found closed or missing is
    forgotten, so one switched on answers its first poll; one switched off
    stops answering the polls of every process within the memory's time.
    """

    def __init__(self) -> None:
        self._open_until: dict[BusinessId, Microseconds] = {}
        self._lock: threading.Lock = threading.Lock()

    def is_open(self, business_id: BusinessId, now: Microseconds) -> bool:
        """Whether the chat was found open less than the memory's time ago."""

        with self._lock:
            open_until: Microseconds | None = self._open_until.get(business_id)

        return open_until is not None and int(now) < int(open_until)

    def remember_open(self, business_id: BusinessId, now: Microseconds) -> None:
        with self._lock:
            self._open_until[business_id] = Microseconds(
                int(now) + OPEN_CHAT_MEMORY_SECONDS * MICROSECONDS_PER_SECOND
            )

    def forget(self, business_id: BusinessId) -> None:
        with self._lock:
            self._open_until.pop(business_id, None)
