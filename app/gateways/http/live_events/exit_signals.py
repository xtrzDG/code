"""
Open live streams end as soon as the API is asked to stop. Uvicorn waits
for running responses before it shuts down (25 s in production, for ever
locally), and a live stream never finishes by itself: on SIGTERM or SIGINT
the streams end first, then uvicorn's own handler runs. The cabinet
reconnects to another instance (or this one once it is back).
"""

import logging
import signal
import threading
from collections.abc import Callable
from types import FrameType

LOGGER: logging.Logger = logging.getLogger(__name__)
EXIT_SIGNALS: tuple[signal.Signals, ...] = (signal.SIGTERM, signal.SIGINT)

type SignalHandler = Callable[[int, FrameType | None], object] | int | None


def end_streams_on_exit_signals(end_streams: Callable[[], None]) -> bool:
    """
    Run `end_streams` before the current handler of each exit signal.
    Only the main thread may set handlers: elsewhere (tests that run the
    app in a thread) nothing changes and False is returned.
    """

    if threading.current_thread() is not threading.main_thread():
        return False

    for exit_signal in EXIT_SIGNALS:
        signal.signal(exit_signal, _chained(end_streams, signal.getsignal(exit_signal)))

    return True


def _chained(
    end_streams: Callable[[], None],
    previous: SignalHandler,
) -> Callable[[int, FrameType | None], None]:
    def handle(signal_number: int, frame: FrameType | None) -> None:
        try:
            end_streams()
        except Exception:  # noqa: BLE001 - the shutdown must go on
            LOGGER.exception("Live streams could not be ended on exit")

        if callable(previous):
            previous(signal_number, frame)
        elif previous == signal.SIG_DFL:
            signal.signal(signal_number, signal.SIG_DFL)
            signal.raise_signal(signal_number)

    return handle
