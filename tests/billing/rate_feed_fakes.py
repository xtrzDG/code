"""Rate feeds over fixture files: the real clients, a fetcher that never dials."""

from collections.abc import Mapping

from app.clients.ecb.ecb_rates_client import ECB_RATES_URL, EcbRatesClient
from app.clients.nbg.nbg_rates_client import NBG_RATES_URL, NbgRatesClient
from app.contracts.web_fetching import SafeHttpFetcherContract
from app.schemas.constants.web_fetching import WebFetchProblem
from app.schemas.dto.web_fetching import FetchedWebResource, WebFetchRequest
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from app.schemas.typings.platform.constrained_strings import ErrorReasonDetail
from app.schemas.typings.web_fetching.constrained_strings import (
    WebMediaType,
    WebResourceUrl,
)
from tests.contracts.contract_files import read_fixture_bytes

# The banks' published feeds (tests/contracts/ecb, tests/contracts/nbg).
NBG_FIXTURE: bytes = read_fixture_bytes("nbg", "nbg_rates.json")
ECB_FIXTURE: bytes = read_fixture_bytes("ecb", "ecb_rates.xml")
type ServedFeed = tuple[str, bytes]


class FixtureFetcher(SafeHttpFetcherContract):
    """Serves the given bodies by address; any other address is refused."""

    def __init__(self, feeds: Mapping[str, ServedFeed]) -> None:
        self._feeds: Mapping[str, ServedFeed] = feeds
        self.requests: list[WebFetchRequest] = []

    def fetch(self, request: WebFetchRequest) -> FetchedWebResource:
        self.requests.append(request)
        served: ServedFeed | None = self._feeds.get(str(request.url))
        if served is None:
            raise WebFetchError(
                "Not served in this test.",
                WebFetchProblem.CONNECTION_FAILED,
                ErrorReasonDetail("connection_failed"),
            )

        media_type, body = served
        return FetchedWebResource(
            url=request.url,
            final_url=request.url,
            media_type=WebMediaType(media_type),
            body=body,
        )

    def vet(self, url: WebResourceUrl) -> None:
        del url


def fixture_fetcher(
    nbg: bytes | None = NBG_FIXTURE, ecb: bytes | None = ECB_FIXTURE
) -> FixtureFetcher:
    feeds: dict[str, ServedFeed] = {}
    if nbg is not None:
        feeds[str(NBG_RATES_URL)] = ("application/json", nbg)
    if ecb is not None:
        feeds[str(ECB_RATES_URL)] = ("text/xml", ecb)
    return FixtureFetcher(feeds)


def fixture_rate_clients(
    fetcher: FixtureFetcher | None = None,
) -> tuple[NbgRatesClient, EcbRatesClient]:
    """The NBG and ECB clients reading the fixture feeds."""

    served: FixtureFetcher = fixture_fetcher() if fetcher is None else fetcher
    return NbgRatesClient(served), EcbRatesClient(served)
