import ssl
import time
from collections.abc import Callable
from urllib.parse import urljoin

import httpcore

from app.clients.http.fetch_errors import fetch_error
from app.clients.http.response_body import read_limited_body, too_large
from app.clients.http.response_headers import (
    header_value,
    read_charset,
    read_media_type,
)
from app.clients.http.url_vetting import VettedUrl, vet_url
from app.clients.http.vetting_network_backend import (
    HostResolver,
    TcpConnector,
    VettingNetworkBackend,
    connect_tcp_address,
    resolve_host_addresses,
)
from app.contracts.web_fetching import SafeHttpFetcherContract
from app.schemas.constants.web_fetching import WebFetchProblem
from app.schemas.dto.web_fetching import FetchedWebResource, WebFetchRequest
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from app.schemas.typings.web_fetching.constrained_strings import (
    WebMediaType,
    WebResourceUrl,
)

MAX_REDIRECTS: int = 3
REDIRECT_STATUSES: frozenset[int] = frozenset({301, 302, 303, 307, 308})
USER_AGENT: str = "AssistantWorkshop-Reader/1.0 (reads a page its owner asked for)"


class SafeHttpFetcher(SafeHttpFetcherContract):
    """
    Reads public web addresses for the platform (SSRF guard):

    - only http(s) on ports 80 and 443, without credentials in the address;
    - every host is resolved and must resolve to public addresses only
      (no loopback, private, link-local, CGNAT or metadata ranges); the
      connection is made to the vetted address itself, which defeats DNS
      rebinding;
    - at most three redirects, each target checked the same way;
    - the body is limited in bytes (after unpacking) and the whole fetch in
      time, and only the requested media types are accepted.

    No proxy is used: the guard must see the address it connects to.
    `resolver`, `connector` and `clock` are replaceable for tests.
    """

    def __init__(
        self,
        resolver: HostResolver = resolve_host_addresses,
        connector: TcpConnector = connect_tcp_address,
        ssl_context: ssl.SSLContext | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._backend: VettingNetworkBackend = VettingNetworkBackend(
            resolver, connector
        )
        self._ssl_context: ssl.SSLContext | None = ssl_context
        self._clock: Callable[[], float] = clock

    def fetch(self, request: WebFetchRequest) -> FetchedWebResource:
        deadline: float = self._clock() + float(request.timeout_seconds)
        current_url: str = str(request.url)
        with httpcore.ConnectionPool(
            ssl_context=self._ssl_context,
            network_backend=self._backend,
            max_connections=1,
            retries=0,
        ) as pool:
            for _ in range(MAX_REDIRECTS + 1):
                vetted: VettedUrl = vet_url(current_url)
                outcome: FetchedWebResource | str = self._fetch_once(
                    pool, vetted, request, deadline
                )
                if isinstance(outcome, FetchedWebResource):
                    return outcome

                current_url = outcome

        raise fetch_error(
            WebFetchProblem.TOO_MANY_REDIRECTS,
            "The address redirects too many times.",
        )

    def _fetch_once(
        self,
        pool: httpcore.ConnectionPool,
        vetted: VettedUrl,
        request: WebFetchRequest,
        deadline: float,
    ) -> FetchedWebResource | str:
        """The resource, or the address the server redirects to."""

        remaining: float = self._remaining(deadline)
        accepted: str = ", ".join(
            sorted(str(kind) for kind in request.accepted_media_types)
        )
        try:
            with pool.stream(
                "GET",
                vetted.request_url,
                headers=[
                    (b"User-Agent", USER_AGENT.encode()),
                    (b"Accept", f"{accepted}, */*;q=0.1".encode()),
                    (b"Accept-Encoding", b"identity"),
                ],
                extensions={
                    "timeout": {
                        "connect": remaining,
                        "read": remaining,
                        "write": remaining,
                        "pool": remaining,
                    }
                },
            ) as response:
                return self._read_response(response, vetted, request, deadline)
        except WebFetchError:
            raise
        except httpcore.TimeoutException as error:
            raise fetch_error(
                WebFetchProblem.TIMEOUT, "The address took too long to answer."
            ) from error
        except httpcore.ConnectError as error:
            raise fetch_error(
                WebFetchProblem.CONNECTION_FAILED, "The address cannot be reached."
            ) from error
        except (httpcore.NetworkError, httpcore.ProtocolError, OSError) as error:
            raise fetch_error(
                WebFetchProblem.REQUEST_FAILED, "The address cannot be read."
            ) from error

    def _read_response(
        self,
        response: httpcore.Response,
        vetted: VettedUrl,
        request: WebFetchRequest,
        deadline: float,
    ) -> FetchedWebResource | str:
        headers: list[tuple[bytes, bytes]] = list(response.headers)
        if response.status in REDIRECT_STATUSES:
            location: str | None = header_value(headers, "location")
            if location is None or location.strip() == "":
                raise fetch_error(
                    WebFetchProblem.REDIRECT_WITHOUT_LOCATION,
                    "The address redirects to nowhere.",
                )

            return urljoin(vetted.request_url, location.strip())

        if response.status >= 300:
            raise fetch_error(
                WebFetchProblem.HTTP_STATUS,
                f"The address answered HTTP {response.status}.",
                str(response.status),
            )

        media_type: str = read_media_type(header_value(headers, "content-type"))
        if media_type not in {str(kind) for kind in request.accepted_media_types}:
            raise fetch_error(
                WebFetchProblem.UNSUPPORTED_MEDIA_TYPE,
                f"The address leads to {media_type}, which cannot be read here.",
                media_type,
            )

        declared_length: str = (header_value(headers, "content-length") or "").strip()
        if declared_length.isdigit() and int(declared_length) > int(request.max_bytes):
            raise too_large(int(request.max_bytes))

        body: bytes = read_limited_body(
            response.iter_stream(),
            header_value(headers, "content-encoding"),
            int(request.max_bytes),
            lambda: self._clock() > deadline,
        )
        return FetchedWebResource(
            url=request.url,
            final_url=WebResourceUrl(vetted.request_url),
            media_type=WebMediaType(media_type),
            charset=read_charset(header_value(headers, "content-type")),
            body=body,
        )

    def _remaining(self, deadline: float) -> float:
        remaining: float = deadline - self._clock()
        if remaining <= 0:
            raise fetch_error(
                WebFetchProblem.TIMEOUT, "The address took too long to read."
            )

        return remaining
