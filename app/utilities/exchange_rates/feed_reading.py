"""Reading a central bank's rate feed through the SSRF-guarded fetcher."""

from datetime import date

from app.contracts.web_fetching import SafeHttpFetcherContract
from app.schemas.constants.billing import ExchangeRateSource
from app.schemas.dto.billing_exchange_rates import (
    ExchangeRateSheet,
    PublishedExchangeRate,
)
from app.schemas.dto.web_fetching import FetchedWebResource, WebFetchRequest
from app.schemas.exceptions.exchange_rate_errors import ExchangeRateFeedError
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from app.schemas.typings.billing.constrained_strings import ExchangeRateDate
from app.schemas.typings.web_fetching.constrained_floats import (
    WebFetchTimeoutSeconds,
)
from app.schemas.typings.web_fetching.constrained_integers import WebFetchByteLimit
from app.schemas.typings.web_fetching.constrained_strings import (
    WebMediaType,
    WebResourceUrl,
)

# A day's rates are a few kilobytes; anything near this is not the feed.
FEED_MAX_BYTES: WebFetchByteLimit = WebFetchByteLimit(512 * 1024)
FEED_TIMEOUT_SECONDS: WebFetchTimeoutSeconds = WebFetchTimeoutSeconds(15.0)
# A sheet with fewer rates than this is a broken feed, not a quiet day.
MIN_SHEET_RATES: int = 5


def read_feed(
    fetcher: SafeHttpFetcherContract,
    url: WebResourceUrl,
    media_types: frozenset[WebMediaType],
) -> bytes:
    """The feed's body; ExchangeRateFeedError when it cannot be read."""

    try:
        resource: FetchedWebResource = fetcher.fetch(
            WebFetchRequest(
                url=url,
                accepted_media_types=media_types,
                max_bytes=FEED_MAX_BYTES,
                timeout_seconds=FEED_TIMEOUT_SECONDS,
            )
        )
    except WebFetchError as error:
        raise ExchangeRateFeedError(
            f"The rate feed {url} was not read: {error}"
        ) from error

    return resource.body


def read_rate_date(text: str | None) -> ExchangeRateDate | None:
    """The day of a feed ("2026-10-02", or its ISO time "2026-10-02T00:00Z")."""

    if text is None:
        return None

    day: str = text.strip()[:10]
    try:
        date.fromisoformat(day)
    except ValueError:
        return None

    return ExchangeRateDate(day)


def build_sheet(
    source: ExchangeRateSource,
    rate_date: ExchangeRateDate | None,
    rates: list[PublishedExchangeRate],
) -> ExchangeRateSheet:
    """The day's sheet; ExchangeRateFeedError without a date or enough rates."""

    if rate_date is None or len(rates) < MIN_SHEET_RATES:
        raise ExchangeRateFeedError(
            f"The {source} rate feed had no date or too few rates ({len(rates)})."
        )

    return ExchangeRateSheet(source=source, rate_date=rate_date, rates=rates)
