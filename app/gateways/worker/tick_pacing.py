"""
The pace of a worker's periodic thread: a tick every WORKER_POLL_SECONDS
(longer and longer after ticks that failed as a whole), and between two
ticks the reaper as often as the worker's quickest lane polls, so a job
whose worker died is due again within moments of its lease's end, not up
to a whole tick later.
"""

import threading
from collections.abc import Callable

# After a tick that failed as a whole (the database is down), wait longer
# and longer between ticks, up to this many seconds.
MAX_TICK_BACKOFF_SECONDS: int = 5 * 60


def tick_pause_seconds(poll_seconds: int, consecutive_failures: int) -> int:
    """The pause before the next tick: the poll, doubled per failed tick."""

    if consecutive_failures == 0:
        return poll_seconds

    backoff_seconds: int = poll_seconds * (1 << min(consecutive_failures, 16))
    return min(backoff_seconds, max(poll_seconds, MAX_TICK_BACKOFF_SECONDS))


def wait_reaping(
    stop_event: threading.Event,
    pause_seconds: float,
    reap_seconds: float,
    reap: Callable[[], object],
) -> None:
    """
    Wait `pause_seconds` (less when `stop_event` is set), calling `reap`
    every `reap_seconds` meanwhile.
    """

    remaining: float = pause_seconds
    while remaining > reap_seconds:
        if stop_event.wait(timeout=reap_seconds):
            return

        reap()
        remaining -= reap_seconds

    stop_event.wait(timeout=remaining)
