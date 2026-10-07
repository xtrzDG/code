import re

from app.contracts.exchange_rate_feeds import ExchangeRateFeedClientContract
from app.contracts.web_fetching import SafeHttpFetcherContract
from app.schemas.constants.billing import ExchangeRateSource
from app.schemas.dto.billing_exchange_rates import (
    ExchangeRateSheet,
    PublishedExchangeRate,
)
from app.schemas.typings.billing.constrained_strings import (
    ExchangeRateDate,
    ExchangeRateValue,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.web_fetching.constrained_strings import (
    WebMediaType,
    WebResourceUrl,
)
from app.utilities.exchange_rates.feed_reading import (
    build_sheet,
    read_feed,
    read_rate_date,
)
from app.utilities.exchange_rates.rate_math import parse_rate_text

ECB_RATES_URL: WebResourceUrl = WebResourceUrl(
    "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
)
XML_MEDIA_TYPES: frozenset[WebMediaType] = frozenset(
    {WebMediaType("text/xml"), WebMediaType("application/xml")}
)
EURO: CurrencyCode = CurrencyCode("EUR")
# The feed's two kinds of Cube element, read by their attributes only: no
# XML parser runs on outside input (no entities, no external references).
DAY_PATTERN: re.Pattern[str] = re.compile(
    r"<Cube\s+time\s*=\s*['\"](\d{4}-\d{2}-\d{2})['\"]\s*>"
)
RATE_PATTERN: re.Pattern[str] = re.compile(
    r"<Cube\s+currency\s*=\s*['\"]([A-Z]{3})['\"]\s+"
    r"rate\s*=\s*['\"]([0-9]{1,12}(?:\.[0-9]{1,12})?)['\"]\s*/>"
)


class EcbRatesClient(ExchangeRateFeedClientContract):
    """
    The European Central Bank's euro foreign exchange reference rates
    (https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/):
    one XML document per TARGET day with about 30 currencies, each the
    units of the currency for one euro. Read through the SSRF-guarded
    fetcher; no key is needed.
    """

    def __init__(
        self,
        safe_http_fetcher: SafeHttpFetcherContract,
        url: WebResourceUrl = ECB_RATES_URL,
    ) -> None:
        self._safe_http_fetcher: SafeHttpFetcherContract = safe_http_fetcher
        self._url: WebResourceUrl = url

    def fetch_latest(self) -> ExchangeRateSheet:
        body: bytes = read_feed(self._safe_http_fetcher, self._url, XML_MEDIA_TYPES)
        return parse_ecb_rates(body)


def parse_ecb_rates(body: bytes) -> ExchangeRateSheet:
    """The ECB's XML as a sheet of EUR -> X rates."""

    text: str = body.decode("utf-8", errors="replace")
    day = DAY_PATTERN.search(text)
    rate_date: ExchangeRateDate | None = read_rate_date(
        None if day is None else day.group(1)
    )
    rates: list[PublishedExchangeRate] = []
    if rate_date is not None:
        for code, rate_text in RATE_PATTERN.findall(text):
            rate: ExchangeRateValue | None = parse_rate_text(rate_text)
            if rate is not None and code != str(EURO):
                rates.append(
                    PublishedExchangeRate(
                        base_currency_code=EURO,
                        quote_currency_code=CurrencyCode(code),
                        rate=rate,
                        rate_date=rate_date,
                        source=ExchangeRateSource.ECB,
                    )
                )

    return build_sheet(ExchangeRateSource.ECB, rate_date, rates)
