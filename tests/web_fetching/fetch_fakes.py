"""A scripted network for the safe fetcher: fake DNS, fake servers, a clock."""

import gzip
from collections.abc import Callable, Mapping, Sequence

import httpcore

from app.clients.http.safe_http_fetcher import SafeHttpFetcher
from app.schemas.dto.web_fetching import FetchedWebResource, WebFetchRequest
from app.schemas.typings.web_fetching.constrained_floats import WebFetchTimeoutSeconds
from app.schemas.typings.web_fetching.constrained_integers import WebFetchByteLimit
from app.schemas.typings.web_fetching.constrained_strings import (
    WebMediaType,
    WebResourceUrl,
)

PUBLIC_ADDRESS: str = "93.184.216.34"
OTHER_PUBLIC_ADDRESS: str = "151.101.1.69"
HTML_TYPES: frozenset[WebMediaType] = frozenset(
    {WebMediaType("text/html"), WebMediaType("text/plain")}
)


def http_response(
    status: int = 200,
    headers: dict[str, str] | None = None,
    body: bytes = b"",
) -> list[bytes]:
    """The bytes a server sends: status line, headers, body."""

    all_headers: dict[str, str] = {"Content-Type": "text/html; charset=utf-8"}
    all_headers.update(headers or {})
    all_headers.setdefault("Content-Length", str(len(body)))
    head: str = f"HTTP/1.1 {status} Status\r\n" + "".join(
        f"{name}: {value}\r\n" for name, value in all_headers.items()
    )
    return [head.encode("latin-1") + b"\r\n", body]


def page(body: str, headers: dict[str, str] | None = None) -> list[bytes]:
    return http_response(200, headers, body.encode("utf-8"))


def redirect(location: str, status: int = 302) -> list[bytes]:
    return http_response(status, {"Location": location, "Content-Type": "text/html"})


def gzipped_page(body: bytes) -> list[bytes]:
    return http_response(200, {"Content-Encoding": "gzip"}, gzip.compress(body))


class FakeNetwork:
    """
    `hosts` maps a host name to the addresses DNS answers (a callable can
    answer differently each time); every connection pops the next scripted
    server answer. Connections and lookups are recorded.
    """

    def __init__(
        self,
        hosts: Mapping[str, list[str] | Callable[[], list[str]]],
        answers: Sequence[list[bytes]] = (),
    ) -> None:
        self._hosts: dict[str, list[str] | Callable[[], list[str]]] = dict(hosts)
        self._answers: list[list[bytes]] = list(answers)
        self.lookups: list[str] = []
        self.connections: list[tuple[str, int]] = []

    def resolve(self, host: str) -> list[str]:
        self.lookups.append(host)
        if host not in self._hosts:
            raise OSError(f"Unknown host {host}")

        addresses: list[str] | Callable[[], list[str]] = self._hosts[host]
        return addresses() if callable(addresses) else list(addresses)

    def connect(
        self, address: str, port: int, timeout: float | None
    ) -> httpcore.NetworkStream:
        del timeout
        self.connections.append((address, port))
        if not self._answers:
            raise AssertionError(f"Unexpected connection to {address}:{port}")

        return httpcore.MockStream(list(self._answers.pop(0)))


class SteppingClock:
    """Each reading is `step` seconds after the previous one."""

    def __init__(self, step: float) -> None:
        self._now: float = 0.0
        self._step: float = step

    def __call__(self) -> float:
        self._now += self._step
        return self._now


def build_fetcher(
    network: FakeNetwork, clock: Callable[[], float] | None = None
) -> SafeHttpFetcher:
    if clock is None:
        return SafeHttpFetcher(resolver=network.resolve, connector=network.connect)

    return SafeHttpFetcher(
        resolver=network.resolve, connector=network.connect, clock=clock
    )


def fetch(
    fetcher: SafeHttpFetcher,
    url: str,
    media_types: frozenset[WebMediaType] = HTML_TYPES,
    max_bytes: int = 5 * 1024 * 1024,
    timeout_seconds: float = 10.0,
) -> FetchedWebResource:
    return fetcher.fetch(
        WebFetchRequest(
            url=WebResourceUrl(url),
            accepted_media_types=media_types,
            max_bytes=WebFetchByteLimit(max_bytes),
            timeout_seconds=WebFetchTimeoutSeconds(timeout_seconds),
        )
    )
