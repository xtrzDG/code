"""Download a menu web page from a public address only."""

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urljoin, urlsplit

import httpx

from app.adapters.llm.menu_extraction.menu_link_problems import link_problem
from app.adapters.llm.menu_extraction.menu_media_content import HTML_MEDIA_TYPE
from app.schemas.constants.menu_import import MenuLinkProblem

type HostResolver = Callable[[str], list[str]]

PAGE_TIMEOUT_SECONDS: float = 10.0
MAX_PAGE_BYTES: int = 10 * 1024 * 1024
MAX_REDIRECTS: int = 3
BLOCKED_HOST_SUFFIXES: tuple[str, ...] = (".localhost", ".local", ".internal")


def download_menu_page(
    url: str,
    page_transport: httpx.BaseTransport | None,
    host_resolver: HostResolver,
) -> tuple[str, bytes]:
    """
    Download a public page; returns its media type and body.

    Raises:
        ValidationFailedError: with a MenuLinkProblem reason when the
            link is not public, cannot be fetched or is too large.
    """

    current_url: str = url
    with httpx.Client(
        transport=page_transport,
        timeout=PAGE_TIMEOUT_SECONDS,
        follow_redirects=False,
    ) as http_client:
        for _ in range(MAX_REDIRECTS + 1):
            require_public_url(current_url, host_resolver)
            try:
                with http_client.stream("GET", current_url) as response:
                    if response.is_redirect:
                        location: str | None = response.headers.get("location")
                        if location is None:
                            raise link_problem(
                                MenuLinkProblem.UNREACHABLE,
                                "The menu link redirects to nowhere.",
                                "redirect_without_location",
                            )

                        current_url = urljoin(current_url, location)
                        continue

                    if response.status_code >= 400:
                        raise link_problem(
                            MenuLinkProblem.UNREACHABLE,
                            f"The menu link answered HTTP {response.status_code}.",
                            f"http_status:{response.status_code}",
                        )

                    return (
                        read_media_type(response.headers.get("content-type")),
                        read_limited_body(response),
                    )
            except httpx.HTTPError as error:
                raise link_problem(
                    MenuLinkProblem.UNREACHABLE,
                    f"The menu link cannot be opened: {type(error).__name__}.",
                    describe_fetch_error(error),
                ) from error

    raise link_problem(
        MenuLinkProblem.UNREACHABLE,
        "The menu link redirects too many times.",
        "too_many_redirects",
    )


def require_public_url(url: str, host_resolver: HostResolver) -> None:
    parts = urlsplit(url)
    host: str = (parts.hostname or "").lower()
    if parts.scheme not in ("http", "https") or host == "":
        raise link_problem(
            MenuLinkProblem.INVALID,
            "The menu link must be an http(s) address.",
            "not_http",
        )

    if host == "localhost" or host.endswith(BLOCKED_HOST_SUFFIXES):
        raise link_problem(
            MenuLinkProblem.INVALID,
            "The menu link must be a public address.",
            "not_public",
        )

    try:
        addresses: list[str] = host_resolver(host)
    except OSError as error:
        raise link_problem(
            MenuLinkProblem.UNREACHABLE,
            "The menu link's host is unknown.",
            "unknown_host",
        ) from error

    if not addresses or any(not is_public_address(address) for address in addresses):
        raise link_problem(
            MenuLinkProblem.INVALID,
            "The menu link must be a public address.",
            "not_public",
        )


def read_media_type(content_type: str | None) -> str:
    if content_type is None:
        return HTML_MEDIA_TYPE

    return content_type.split(";", 1)[0].strip().lower()


def read_limited_body(response: httpx.Response) -> bytes:
    body = bytearray()
    for chunk in response.iter_bytes():
        body.extend(chunk)
        if len(body) > MAX_PAGE_BYTES:
            raise link_problem(
                MenuLinkProblem.UNREADABLE,
                "The menu behind the link is larger than 10 MB.",
                "too_large",
            )

    return bytes(body)


def describe_fetch_error(error: httpx.HTTPError) -> str:
    """Detail of a failed page download: timeout, connection or other."""

    if isinstance(error, httpx.TimeoutException):
        return "timeout"

    if isinstance(error, httpx.ConnectError):
        return "connection_failed"

    return "request_failed"


def resolve_host_addresses(host: str) -> list[str]:
    """IP addresses a host name resolves to (raises OSError when unknown)."""

    return sorted(
        {
            str(info[4][0])
            for info in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        }
    )


def is_public_address(address: str) -> bool:
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False

    return parsed.is_global and not parsed.is_multicast
