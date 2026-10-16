"""
A connection with one deadline for everything sent and read on it.

httpcore's timeouts bound each read or write on its own, so a server that
trickles a byte every few seconds (headers that never end, a body that
never finishes) would hold a worker thread for as long as it likes. Every
connect, TLS handshake, read and write is bounded by the time left until
the deadline, and past it the next one fails at once.
"""

from collections.abc import Callable
from ssl import SSLContext
from typing import Any

import httpcore

PAST_DEADLINE_MESSAGE: str = "The address took too long altogether."

type TimeoutKind = type[httpcore.TimeoutException]


def time_left(
    deadline: float,
    clock: Callable[[], float],
    timeout: float | None,
    kind: TimeoutKind = httpcore.ConnectTimeout,
) -> float:
    """
    An operation's timeout cut to the time left until `deadline`.

    Raises:
        httpcore.TimeoutException: `kind`, when no time is left.
    """

    remaining: float = deadline - clock()
    if remaining <= 0:
        raise kind(PAST_DEADLINE_MESSAGE)

    return remaining if timeout is None else min(timeout, remaining)


class DeadlineNetworkStream(httpcore.NetworkStream):
    """Wraps a stream so no operation on it outlasts `deadline` (of `clock`)."""

    def __init__(
        self,
        stream: httpcore.NetworkStream,
        deadline: float,
        clock: Callable[[], float],
    ) -> None:
        self._stream: httpcore.NetworkStream = stream
        self._deadline: float = deadline
        self._clock: Callable[[], float] = clock

    def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        return self._stream.read(
            max_bytes,
            time_left(self._deadline, self._clock, timeout, httpcore.ReadTimeout),
        )

    def write(self, buffer: bytes, timeout: float | None = None) -> None:
        self._stream.write(
            buffer,
            time_left(self._deadline, self._clock, timeout, httpcore.WriteTimeout),
        )

    def close(self) -> None:
        self._stream.close()

    def start_tls(
        self,
        ssl_context: SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> httpcore.NetworkStream:
        secured: httpcore.NetworkStream = self._stream.start_tls(
            ssl_context,
            server_hostname,
            time_left(self._deadline, self._clock, timeout),
        )
        return DeadlineNetworkStream(secured, self._deadline, self._clock)

    def get_extra_info(self, info: str) -> Any:
        return self._stream.get_extra_info(info)
