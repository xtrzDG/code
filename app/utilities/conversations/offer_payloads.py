"""
Bookable offers, stay quotes and booking values as the language model
reads them in tool results (amounts in major units next to the currency,
as every other price in `tool_payloads`).
"""

from collections.abc import Sequence

from app.schemas.domain.knowledge import SeasonalNightlyRate
from app.schemas.dto.billing import Money
from app.schemas.dto.bookable_offers import BookableOfferView, StayQuote
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.money.money_math import (
    convert_money_to_major_units,
    get_currency_minor_unit_digits,
)


def major_units(amount_minor: int, currency_code: CurrencyCode) -> str:
    """51700 GEL minor units -> "517.00" (the currency's own precision)."""

    money = Money(
        amount_minor=MoneyAmountMinor(amount_minor), currency_code=currency_code
    )
    digits: int = int(get_currency_minor_unit_digits(currency_code))
    return f"{convert_money_to_major_units(money):.{digits}f}"


def render_offer(offer: BookableOfferView) -> dict[str, object]:
    """One bookable service with its id, length, price and performers."""

    rendered: dict[str, object] = {
        "service_id": str(offer.id),
        "kind": offer.kind.value,
        "title": str(offer.title),
    }
    if offer.duration_minutes is not None:
        rendered["duration_minutes"] = int(offer.duration_minutes)

    if offer.price_minor is not None and offer.currency_code is not None:
        rendered["price"] = major_units(int(offer.price_minor), offer.currency_code)
        rendered["currency"] = str(offer.currency_code)

    if offer.performers:
        rendered["performed_by"] = [
            {
                "resource_id": str(performer.resource_id),
                "name": str(performer.resource_name),
            }
            for performer in offer.performers
        ]

    return rendered


def render_stay_quote(quote: StayQuote) -> dict[str, object]:
    """A stay's total and each night's rate (with its season's name)."""

    return {
        "service_id": str(quote.item_id),
        "title": str(quote.item_title),
        "check_in": str(quote.check_in),
        "check_out": str(quote.check_out),
        "nights": int(quote.nights),
        "total": major_units(int(quote.total_minor), quote.currency_code),
        "currency": str(quote.currency_code),
        "nightly": [
            {
                "date": str(night.date),
                "rate": major_units(int(night.nightly_rate_minor), quote.currency_code),
                **(
                    {}
                    if night.season_name is None
                    else {"season": str(night.season_name)}
                ),
            }
            for night in quote.night_prices
        ],
    }


def render_seasons(
    seasons: Sequence[SeasonalNightlyRate],
    currency_code: CurrencyCode,
) -> list[dict[str, object]]:
    """Seasonal nightly rates: from and to as "MM-DD", every year."""

    return [
        {
            "from": str(season.starts_on),
            "to": str(season.ends_on),
            "nightly_rate": major_units(int(season.nightly_rate_minor), currency_code),
            **({} if season.name is None else {"season": str(season.name)}),
        }
        for season in seasons
    ]
