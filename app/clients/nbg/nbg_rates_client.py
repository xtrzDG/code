import json
from typing import cast

from app.contracts.exchange_rate_feeds import ExchangeRateFeedClientContract
from app.contracts.web_fetching import SafeHttpFetcherContract
from app.schemas.constants.billing import ExchangeRateSource
from app.schemas.dto.billing_exchange_rates import (
    ExchangeRateSheet,
    PublishedExchangeRate,
)
from app.schemas.exceptions.exchange_rate_errors import ExchangeRateFeedError
from app.schemas.typings.billing.constrained_strings import (
    ExchangeRateDate,
    ExchangeRateValue,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.web_fetching.constrained_strings import (
    WebMediaType,
    WebResourceUrl,
)
from app.utilities.channels.json_values import JsonObject, as_object, read_objects
from app.utilities.exchange_rates.feed_reading import (
    build_sheet,
    read_feed,
    read_rate_date,
)
from app.utilities.exchange_rates.rate_math import parse_rate_text

NBG_RATES_URL: WebResourceUrl = WebResourceUrl(
    "https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/"
)
JSON_MEDIA_TYPES: frozenset[WebMediaType] = frozenset(
    {WebMediaType("application/json")}
)
LARI: CurrencyCode = CurrencyCode("GEL")
CURRENCY_CODE_LENGTH: int = 3


class NbgRatesClient(ExchangeRateFeedClientContract):
    """
    The National Bank of Georgia's official rates of the lari
    (https://nbg.gov.ge/en/monetary-policy/currency): one JSON list whose
    first item holds the day ("date") and about 40 currencies, each a rate
    in GEL for `quantity` units ("rateFormated" "0.6884" for 100 AMD).
    Read through the SSRF-guarded fetcher; no key is needed.
    """

    def __init__(
        self,
        safe_http_fetcher: SafeHttpFetcherContract,
        url: WebResourceUrl = NBG_RATES_URL,
    ) -> None:
        self._safe_http_fetcher: SafeHttpFetcherContract = safe_http_fetcher
        self._url: WebResourceUrl = url

    def fetch_latest(self) -> ExchangeRateSheet:
        body: bytes = read_feed(self._safe_http_fetcher, self._url, JSON_MEDIA_TYPES)
        return parse_nbg_rates(body)


def parse_nbg_rates(body: bytes) -> ExchangeRateSheet:
    """The NBG's JSON as a sheet of X -> GEL rates (per one unit of X)."""

    try:
        document: object = json.loads(body)
    except ValueError, UnicodeDecodeError:
        raise ExchangeRateFeedError("The NBG rate feed is not JSON.") from None

    items: list[object] = (
        cast(list[object], document) if isinstance(document, list) else [document]
    )
    day: JsonObject | None = as_object(items[0]) if items else None
    if day is None:
        raise ExchangeRateFeedError("The NBG rate feed holds no day.")

    rate_date: ExchangeRateDate | None = read_rate_date(text_of(day.get("date")))
    rates: list[PublishedExchangeRate] = []
    if rate_date is not None:
        for currency in read_objects(day, "currencies"):
            rate: PublishedExchangeRate | None = read_currency(currency, rate_date)
            if rate is not None:
                rates.append(rate)

    return build_sheet(ExchangeRateSource.NBG, rate_date, rates)


def read_currency(
    currency: JsonObject, rate_date: ExchangeRateDate
) -> PublishedExchangeRate | None:
    code: str | None = text_of(currency.get("code"))
    quantity: object = currency.get("quantity")
    rate_text: str | None = text_of(currency.get("rateFormated")) or text_of(
        currency.get("rate")
    )
    if (
        code is None
        or len(code) != CURRENCY_CODE_LENGTH
        or not code.isalpha()
        or not code.isupper()
        or code == str(LARI)
        or rate_text is None
    ):
        return None

    is_count: bool = isinstance(quantity, int) and not isinstance(quantity, bool)
    per_units: int = quantity if is_count and isinstance(quantity, int) else 1
    rate: ExchangeRateValue | None = parse_rate_text(rate_text, per_units)
    if rate is None:
        return None

    return PublishedExchangeRate(
        base_currency_code=CurrencyCode(code),
        quote_currency_code=LARI,
        rate=rate,
        rate_date=rate_date,
        source=ExchangeRateSource.NBG,
    )


def text_of(value: object) -> str | None:
    """A string, or a number's decimal text (NBG sends both)."""

    if isinstance(value, bool):
        return None

    if isinstance(value, int | float):
        return repr(value)

    if isinstance(value, str) and value.strip() != "":
        return value.strip()

    return None
