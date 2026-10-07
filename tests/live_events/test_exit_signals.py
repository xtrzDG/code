"""Live streams end first when the API is asked to stop."""

import signal
import threading
from collections.abc import Iterator
from types import FrameType

import pytest

from app.gateways.http.live_events import exit_signals
from app.gateways.http.live_events.exit_signals import end_streams_on_exit_signals


@pytest.fixture(autouse=True)
def restore_handlers() -> Iterator[None]:
    saved = {sig: signal.getsignal(sig) for sig in exit_signals.EXIT_SIGNALS}
    yield
    for sig, handler in saved.items():
        signal.signal(sig, handler)


def current_handler(sig: signal.Signals) -> exit_signals.SignalHandler:
    return signal.getsignal(sig)


def test_the_streams_end_before_the_server_handles_the_signal() -> None:
    calls: list[str] = []

    def server_handler(signal_number: int, frame: FrameType | None) -> None:
        calls.append(f"server {signal_number}")

    signal.signal(signal.SIGTERM, server_handler)

    assert end_streams_on_exit_signals(lambda: calls.append("streams ended"))
    handler = current_handler(signal.SIGTERM)
    assert callable(handler)
    handler(signal.SIGTERM, None)

    assert calls == ["streams ended", f"server {int(signal.SIGTERM)}"]


def test_a_failing_end_does_not_stop_the_shutdown() -> None:
    calls: list[int] = []

    def fail() -> None:
        raise RuntimeError("the bus is gone")

    signal.signal(signal.SIGINT, lambda number, frame: calls.append(number))
    end_streams_on_exit_signals(fail)
    handler = current_handler(signal.SIGINT)
    assert callable(handler)
    handler(signal.SIGINT, None)

    assert calls == [int(signal.SIGINT)]


def test_a_default_handler_is_raised_again_and_an_ignored_one_stays_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raised: list[int] = []
    monkeypatch.setattr(signal, "raise_signal", raised.append)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    ended: list[int] = []
    end_streams_on_exit_signals(lambda: ended.append(1))

    for sig in (signal.SIGTERM, signal.SIGINT):
        handler = current_handler(sig)
        assert callable(handler)
        handler(sig, None)

    assert ended == [1, 1]
    assert raised == [signal.SIGTERM]
    assert signal.getsignal(signal.SIGTERM) == signal.SIG_DFL


def test_outside_the_main_thread_nothing_changes() -> None:
    before = current_handler(signal.SIGTERM)
    results: list[bool] = []
    thread = threading.Thread(
        target=lambda: results.append(end_streams_on_exit_signals(lambda: None))
    )
    thread.start()
    thread.join()

    assert results == [False]
    assert current_handler(signal.SIGTERM) == before
