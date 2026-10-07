"""Inputs shared by the billing text tests: Tbilisi moments and GEL amounts."""

from datetime import datetime
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.schemas.dto.billing import Money
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.billing.billing_periods import to_microseconds

TBILISI = "Asia/Tbilisi"


def tbilisi(year: int, month: int, day: int, hour: int, minute: int) -> Microseconds:
    return to_microseconds(
        datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(TBILISI))
    )


def gel(amount_minor: int) -> Money:
    return Money(
        amount_minor=MoneyAmountMinor(amount_minor),
        currency_code=CurrencyCode("GEL"),
    )
