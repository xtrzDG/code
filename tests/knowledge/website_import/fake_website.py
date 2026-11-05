"""A website served from memory to the real safe fetcher: pages by address."""

from collections.abc import Callable, Mapping
from typing import Any

import httpcore

from tests.web_fetching.fetch_fakes import http_response

type HostAnswer = list[str] | Callable[[], list[str]]


class FakeWebsite:
    """
    DNS answers per host and responses per absolute address; an unknown
    address answers 404. Every request is recorded as the address it asked
    for, so tests see which pages the import read and in what order.
    """

    def __init__(
        self,
        hosts: Mapping[str, HostAnswer],
        pages: Mapping[str, list[bytes]],
    ) -> None:
        self._hosts: dict[str, HostAnswer] = dict(hosts)
        self.pages: dict[str, list[bytes]] = dict(pages)
        self.requested: list[str] = []
        self.connections: list[tuple[str, int]] = []

    def add_host(self, host: str, answer: HostAnswer) -> None:
        self._hosts[host] = answer

    def resolve(self, host: str) -> list[str]:
        if host not in self._hosts:
            raise OSError(f"Unknown host {host}")

        answer: HostAnswer = self._hosts[host]
        return answer() if callable(answer) else list(answer)

    def connect(
        self, address: str, port: int, timeout: float | None
    ) -> httpcore.NetworkStream:
        del timeout
        self.connections.append((address, port))
        return RoutingStream(self, "https" if port == 443 else "http")

    def answer(self, url: str) -> list[bytes]:
        self.requested.append(url)
        return list(self.pages.get(url, http_response(404)))


class RoutingStream(httpcore.NetworkStream):
    """Answers each request written to it with the page of its address."""

    def __init__(self, website: FakeWebsite, scheme: str) -> None:
        self._website: FakeWebsite = website
        self._scheme: str = scheme
        self._incoming: bytes = b""
        self._outgoing: list[bytes] = []

    def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        del max_bytes, timeout
        return self._outgoing.pop(0) if self._outgoing else b""

    def write(self, buffer: bytes, timeout: float | None = None) -> None:
        del timeout
        self._incoming += buffer
        while b"\r\n\r\n" in self._incoming:
            head, _, self._incoming = self._incoming.partition(b"\r\n\r\n")
            lines: list[str] = head.decode("latin-1").split("\r\n")
            target: str = lines[0].split(" ")[1]
            host: str = next(
                line.split(":", 1)[1].strip()
                for line in lines[1:]
                if line.lower().startswith("host:")
            )
            self._outgoing.extend(
                self._website.answer(f"{self._scheme}://{host}{target}")
            )

    def close(self) -> None:
        self._outgoing.clear()

    def start_tls(
        self,
        ssl_context: Any,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> httpcore.NetworkStream:
        del ssl_context, server_hostname, timeout
        return self

    def get_extra_info(self, info: str) -> Any:
        del info
        return None
