from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.schemas.constants.billing import ExchangeRateSource
from app.schemas.typings.billing.booleans import IsDerivedExchangeRate
from app.schemas.typings.billing.constrained_integers import ExchangeRateDayNumber
from app.schemas.typings.billing.constrained_strings import (
    CurrencyPairCode,
    ExchangeRateDate,
    ExchangeRateValue,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode


class ExchangeRateDocument(BaseDocument):
    """
    One published exchange rate of one day (platform-wide, migration 1071):
    `rate` units of the quote currency for one unit of the base currency,
    exactly as a decimal string. Rates are dated data: every day keeps its
    row, and the newest row of a pair (`pair`, `rate_day`) is the current
    rate. `is_derived` marks a rate the refresh computed from two published
    ones (EUR -> AMD from the NBG's EUR -> GEL and AMD -> GEL) rather than
    one a bank published itself.
    """

    base_currency_code: CurrencyCode
    quote_currency_code: CurrencyCode
    pair: CurrencyPairCode
    rate: ExchangeRateValue
    rate_date: ExchangeRateDate
    rate_day: ExchangeRateDayNumber
    source: ExchangeRateSource
    is_derived: IsDerivedExchangeRate = False
    fetched_at: Microseconds
