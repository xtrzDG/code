"""
A scripted network of iCal feeds for the safe-fetcher seam: registered
addresses answer their calendar text, every other one is an unknown host;
an address can be made to time out or answer with an HTTP error, and
`on_fetch` runs while a feed is read. The real vetting rules apply.
"""

from collections.abc import Callable

from app.clients.http.fetch_errors import fetch_error
from app.clients.http.url_vetting import vet_url
from app.contracts.web_fetching import SafeHttpFetcherContract
from app.schemas.constants.web_fetching import WebFetchProblem
from app.schemas.dto.web_fetching import FetchedWebResource, WebFetchRequest
from app.schemas.typings.web_fetching.constrained_strings import (
    WebMediaType,
    WebResourceUrl,
)


class CalendarFeedServer(SafeHttpFetcherContract):
    """Feeds by address; `fetched` lists every address read, in order."""

    def __init__(self) -> None:
        self.feeds: dict[str, bytes] = {}
        self.slow: set[str] = set()
        self.fetched: list[str] = []
        self.time_limits: list[float] = []
        self.statuses: dict[str, int] = {}
        self.on_fetch: Callable[[str], None] | None = None

    def serve(self, url: str, body: str) -> None:
        self.feeds[url] = body.encode("utf-8")

    def fetch(self, request: WebFetchRequest) -> FetchedWebResource:
        url: str = str(request.url)
        vet_url(url)
        self.fetched.append(url)
        self.time_limits.append(float(request.timeout_seconds))
        if self.on_fetch is not None:
            self.on_fetch(url)
        if url in self.slow:
            raise fetch_error(WebFetchProblem.TIMEOUT, "The address took too long.")
        if url in self.statuses:
            raise fetch_error(
                WebFetchProblem.HTTP_STATUS, "HTTP error.", str(self.statuses[url])
            )
        body: bytes | None = self.feeds.get(url)
        if body is None:
            raise fetch_error(WebFetchProblem.UNKNOWN_HOST, "Unknown host.")

        return FetchedWebResource(
            url=request.url,
            final_url=request.url,
            media_type=WebMediaType("text/calendar"),
            body=body,
        )

    def vet(self, url: WebResourceUrl) -> None:
        vet_url(str(url))
