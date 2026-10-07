"""
Connections only to vetted public addresses, made to the very address
that was vetted (DNS rebinding cannot swap it between check and use),
and, with a deadline, nothing on them outlasts it.
"""

import socket
import time
from collections.abc import Callable, Iterable

import httpcore

from app.clients.http.deadline_network_stream import DeadlineNetworkStream, time_left
from app.clients.http.fetch_errors import fetch_error
from app.clients.http.public_addresses import is_public_address
from app.schemas.constants.web_fetching import WebFetchProblem

type HostResolver = Callable[[str], list[str]]
type TcpConnector = Callable[[str, int, float | None], httpcore.NetworkStream]


def resolve_host_addresses(host: str) -> list[str]:
    """Every address a host resolves to, in the resolver's order."""

    addresses: list[str] = []
    for info in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM):
        address: str = str(info[4][0])
        if address not in addresses:
            addresses.append(address)

    return addresses


def connect_tcp_address(
    address: str, port: int, timeout: float | None
) -> httpcore.NetworkStream:
    """A plain TCP connection to an IP address (never a host name)."""

    return httpcore.SyncBackend().connect_tcp(address, port, timeout=timeout)


class VettingNetworkBackend(httpcore.NetworkBackend):
    """
    httpcore asks it for a connection to the host and port of a URL; it
    resolves the host once, refuses the host when any address it resolves
    to is not public, and connects to those vetted addresses only. TLS is
    then negotiated by httpcore with the host name (SNI and certificate
    checks are unchanged). With a `deadline` (of `clock`), the connection
    and every read and write on it end by then, however slowly the server
    answers (`DeadlineNetworkStream`).
    """

    def __init__(
        self,
        resolver: HostResolver,
        connector: TcpConnector,
        deadline: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._resolver: HostResolver = resolver
        self._connector: TcpConnector = connector
        self._deadline: float | None = deadline
        self._clock: Callable[[], float] = clock

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.NetworkStream:
        del local_address, socket_options
        addresses: list[str] = self._resolve(host)
        if not addresses:
            raise fetch_error(
                WebFetchProblem.UNKNOWN_HOST, "The address's host is unknown."
            )

        if not all(is_public_address(address) for address in addresses):
            raise fetch_error(
                WebFetchProblem.NOT_PUBLIC, "The address must be a public address."
            )

        last_error: Exception | None = None
        for address in addresses:
            try:
                return self._bounded(self._connect(address, port, timeout))
            except (OSError, httpcore.ConnectError) as error:
                last_error = error

        message: str = f"No address of {host} accepted the connection."
        raise httpcore.ConnectError(message) from last_error

    def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.NetworkStream:
        del path, timeout, socket_options
        raise fetch_error(
            WebFetchProblem.NOT_HTTP, "Only http and https addresses can be read."
        )

    def _connect(
        self, address: str, port: int, timeout: float | None
    ) -> httpcore.NetworkStream:
        if self._deadline is None:
            return self._connector(address, port, timeout)

        return self._connector(
            address, port, time_left(self._deadline, self._clock, timeout)
        )

    def _bounded(self, stream: httpcore.NetworkStream) -> httpcore.NetworkStream:
        if self._deadline is None:
            return stream

        return DeadlineNetworkStream(stream, self._deadline, self._clock)

    def _resolve(self, host: str) -> list[str]:
        try:
            return self._resolver(host)
        except (OSError, UnicodeError) as error:
            raise fetch_error(
                WebFetchProblem.UNKNOWN_HOST, "The address's host is unknown."
            ) from error
