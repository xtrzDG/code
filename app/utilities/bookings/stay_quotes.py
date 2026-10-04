"""
Nightly rates by season and the price of a stay.

A season runs from its first to its last month and day (both included)
every year, over New Year when the last day comes first ("12-20" to
"01-10"). A night takes the rate of the first season it falls into, else
the item's own price; a stay costs the sum of its nights, so a stay across
two seasons is priced night by night.
"""

from datetime import date, timedelta

from app.schemas.domain.knowledge import KnowledgeItemDocument, SeasonalNightlyRate
from app.schemas.dto.bookable_offers import StayNightPrice, StayQuote
from app.schemas.typings.bookings.constrained_integers import NightCount
from app.schemas.typings.knowledge.constrained_integers import (
    NightlyRateMinor,
    StayPriceMinor,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.scheduling.nights import stay_dates
from app.utilities.scheduling.zoned_time import to_local_date


def month_day(night: date) -> str:
    """ "MM-DD" of a date, comparable with a season's days as text."""

    return f"{night.month:02d}-{night.day:02d}"


def is_in_season(night: date, season: SeasonalNightlyRate) -> bool:
    day: str = month_day(night)
    starts: str = str(season.starts_on)
    ends: str = str(season.ends_on)
    if starts <= ends:
        return starts <= day <= ends

    return day >= starts or day <= ends


def price_night(item: KnowledgeItemDocument, night: date) -> StayNightPrice | None:
    """The rate of the night starting on `night`; None without any price."""

    for season in item.seasonal_rates:
        if is_in_season(night, season):
            return StayNightPrice(
                date=to_local_date(night),
                nightly_rate_minor=season.nightly_rate_minor,
                season_name=season.name,
            )

    if item.price_minor is None:
        return None

    return StayNightPrice(
        date=to_local_date(night),
        nightly_rate_minor=NightlyRateMinor(int(item.price_minor)),
    )


def quote_stay(
    item: KnowledgeItemDocument,
    check_in: date,
    nights: int,
    business_currency_code: CurrencyCode,
) -> StayQuote | None:
    """
    The price of `nights` nights from `check_in`; None when a night has no
    rate (no season covers it and the item has no price).
    """

    night_prices: list[StayNightPrice] = []
    for night in stay_dates(check_in, nights):
        price: StayNightPrice | None = price_night(item, night)
        if price is None:
            return None

        night_prices.append(price)

    return StayQuote(
        item_id=item.id,
        item_title=item.title,
        check_in=to_local_date(check_in),
        check_out=to_local_date(check_in + timedelta(days=nights)),
        nights=NightCount(nights),
        currency_code=item.currency_code or business_currency_code,
        total_minor=StayPriceMinor(
            sum(int(price.nightly_rate_minor) for price in night_prices)
        ),
        night_prices=night_prices,
    )
