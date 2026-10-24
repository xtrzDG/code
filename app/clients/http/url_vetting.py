"""
The checks an address passes before any lookup or connection: http(s),
no credentials, port 80 or 443, a host name that is not an intranet name
and, when the host is an IP literal, a public one. The host's DNS answer
is checked later, when the connection is made (`VettingNetworkBackend`).
"""

from dataclasses import dataclass
from urllib.parse import SplitResult, quote, urlsplit, urlunsplit

from app.clients.http.fetch_errors import fetch_error
from app.clients.http.public_addresses import (
    ALLOWED_PORTS,
    is_blocked_host_name,
    is_public_address,
    parse_ip_address,
)
from app.schemas.constants.web_fetching import WebFetchProblem

DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443}
# Characters kept as they are when a path or query is percent-encoded.
SAFE_PATH_CHARACTERS: str = "/%:@!$&'()*+,;=-._~"
SAFE_QUERY_CHARACTERS: str = SAFE_PATH_CHARACTERS + "?"


@dataclass(frozen=True)
class VettedUrl:
    """An address that passed the static checks, ready for the request line."""

    scheme: str
    host: str
    port: int
    # The address without its fragment, the host in ASCII (IDNA).
    request_url: str


def vet_url(url: str) -> VettedUrl:
    """
    Raises:
        WebFetchError: NOT_HTTP, CREDENTIALS_IN_URL, PORT_NOT_ALLOWED or
            NOT_PUBLIC.
    """

    try:
        parts: SplitResult = urlsplit(url.strip())
        port: int | None = parts.port
    except ValueError as error:
        raise fetch_error(
            WebFetchProblem.NOT_HTTP, "The address is not a valid http(s) address."
        ) from error

    scheme: str = parts.scheme.lower()
    raw_host: str = (parts.hostname or "").rstrip(".").lower()
    if scheme not in DEFAULT_PORTS or raw_host == "":
        raise fetch_error(
            WebFetchProblem.NOT_HTTP, "Only http and https addresses can be read."
        )

    if parts.username is not None or parts.password is not None:
        raise fetch_error(
            WebFetchProblem.CREDENTIALS_IN_URL,
            "Addresses with a user name or password are not read.",
        )

    effective_port: int = DEFAULT_PORTS[scheme] if port is None else port
    if effective_port not in ALLOWED_PORTS:
        raise fetch_error(
            WebFetchProblem.PORT_NOT_ALLOWED,
            "Only addresses on the standard ports 80 and 443 are read.",
        )

    host: str = to_ascii_host(raw_host)
    is_literal: bool = parse_ip_address(host) is not None
    if is_blocked_host_name(host) or (is_literal and not is_public_address(host)):
        raise fetch_error(
            WebFetchProblem.NOT_PUBLIC, "The address must be a public address."
        )

    netloc: str = f"[{host}]" if ":" in host else host
    if port is not None:
        netloc = f"{netloc}:{port}"

    return VettedUrl(
        scheme=scheme,
        host=host,
        port=effective_port,
        request_url=urlunsplit(
            (
                scheme,
                netloc,
                quote(parts.path or "/", safe=SAFE_PATH_CHARACTERS),
                quote(parts.query, safe=SAFE_QUERY_CHARACTERS),
                "",
            )
        ),
    )


def to_ascii_host(host: str) -> str:
    """The host as DNS knows it: an international name in its IDNA form."""

    if parse_ip_address(host) is not None or host.isascii():
        return host

    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise fetch_error(
            WebFetchProblem.NOT_HTTP, "The address has an invalid host name."
        ) from error
