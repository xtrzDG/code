"""
The bridge between the live event bus and one open SSE response: the bus
delivers from any thread (the LISTEN thread, a request thread, the embedded
worker), the response reads on the event loop.
"""

import asyncio
import logging
from enum import Enum

from app.contracts.live_events import LiveEventSubscriberContract
from app.schemas.dto.live_events import LiveEvent

LOGGER: logging.Logger = logging.getLogger(__name__)
# Events waiting for a slow client; past this the stream asks the cabinet
# to reload instead (it would reload for each of them anyway).
DEFAULT_QUEUE_CAPACITY: int = 256


class StreamControl(Enum):
    """What the bus tells a stream besides events."""

    RESYNC = "resync"
    END = "end"


type StreamItem = LiveEvent | StreamControl


class EventStreamSubscriber(LiveEventSubscriberContract):
    """
    Thread-safe: `deliver`, `resync` and `end` hand their item to the event
    loop of the response (`call_soon_threadsafe`) and return at once. A
    queue that overflows collapses into one RESYNC.
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        capacity: int = DEFAULT_QUEUE_CAPACITY,
    ) -> None:
        self._loop: asyncio.AbstractEventLoop = loop
        self._capacity: int = capacity
        self._queue: asyncio.Queue[StreamItem] = asyncio.Queue()

    def deliver(self, event: LiveEvent) -> None:
        self._hand_over(event)

    def resync(self) -> None:
        self._hand_over(StreamControl.RESYNC)

    def end(self) -> None:
        self._hand_over(StreamControl.END)

    async def next_item(self, timeout_seconds: float) -> StreamItem | None:
        """The next item, or None when nothing came within the timeout."""

        try:
            return await asyncio.wait_for(self._queue.get(), timeout_seconds)
        except TimeoutError:
            return None

    def _hand_over(self, item: StreamItem) -> None:
        try:
            self._loop.call_soon_threadsafe(self._put, item)
        except RuntimeError:
            # The response's loop is closed: the stream is gone already.
            LOGGER.debug("A live event reached a closed stream")

    def _put(self, item: StreamItem) -> None:
        if item is StreamControl.END or self._queue.qsize() < self._capacity:
            self._queue.put_nowait(item)
            return

        while not self._queue.empty():
            self._queue.get_nowait()

        self._queue.put_nowait(StreamControl.RESYNC)
