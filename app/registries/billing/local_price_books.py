"""
The local price books: what each plan costs in the currencies the platform
bills in besides the plans' own euros.

Every amount is set here by hand, in whole units of its currency and
rounded the way a price is read in that market (293 lari as the concept
lists them; $109, 42 900 ֏, ₪399, 55 900 ₸, 429 zł), never converted from
the euro price with an exchange rate: a rate that moves never changes what
an owner pays. A business is billed in its own currency only when the book
has both the monthly price and the done-for-you setup fee of its plan in
that currency (`select_subscription_currency`); each book also prices the
further locations of a brand. The lari amounts are the concept's; the
others are the product's own, at about the euro price.
"""

from app.schemas.constants.billing import PlanKey
from app.schemas.dto.billing import Money
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import CurrencyCode

# Every currency of the books has two minor-unit digits (ISO 4217).
MINOR_UNITS_PER_MAJOR: int = 100

GEORGIAN_LARI: CurrencyCode = CurrencyCode("GEL")
US_DOLLAR: CurrencyCode = CurrencyCode("USD")
ARMENIAN_DRAM: CurrencyCode = CurrencyCode("AMD")
ISRAELI_SHEKEL: CurrencyCode = CurrencyCode("ILS")
KAZAKHSTANI_TENGE: CurrencyCode = CurrencyCode("KZT")
POLISH_ZLOTY: CurrencyCode = CurrencyCode("PLN")

# Whole units of each currency, per plan: (monthly price, done-for-you
# setup fee, monthly price of each further location of a brand).
type PlanPrices = tuple[int, int, int]

PRICE_TABLE: dict[CurrencyCode, dict[PlanKey, PlanPrices]] = {
    GEORGIAN_LARI: {
        PlanKey.CHAT: (293, 443, 204),
        PlanKey.VOICE_AND_CHAT: (517, 443, 369),
        PlanKey.PLUS: (1031, 443, 735),
    },
    US_DOLLAR: {
        PlanKey.CHAT: (109, 169, 79),
        PlanKey.VOICE_AND_CHAT: (199, 169, 139),
        PlanKey.PLUS: (389, 169, 279),
    },
    ARMENIAN_DRAM: {
        PlanKey.CHAT: (42_900, 64_900, 29_900),
        PlanKey.VOICE_AND_CHAT: (75_900, 64_900, 53_900),
        PlanKey.PLUS: (149_900, 64_900, 106_900),
    },
    ISRAELI_SHEKEL: {
        PlanKey.CHAT: (399, 599, 279),
        PlanKey.VOICE_AND_CHAT: (699, 599, 499),
        PlanKey.PLUS: (1399, 599, 999),
    },
    KAZAKHSTANI_TENGE: {
        PlanKey.CHAT: (55_900, 83_900, 38_900),
        PlanKey.VOICE_AND_CHAT: (97_900, 83_900, 69_900),
        PlanKey.PLUS: (195_900, 83_900, 139_900),
    },
    POLISH_ZLOTY: {
        PlanKey.CHAT: (429, 649, 299),
        PlanKey.VOICE_AND_CHAT: (749, 649, 539),
        PlanKey.PLUS: (1499, 649, 1069),
    },
}

MONTHLY_PRICE_COLUMN: int = 0
SETUP_FEE_COLUMN: int = 1
ADDITIONAL_LOCATION_COLUMN: int = 2


def build_local_price(currency_code: CurrencyCode, whole_units: int) -> Money:
    """A price-book amount: whole units of the currency, in minor units."""

    return Money(
        amount_minor=MoneyAmountMinor(whole_units * MINOR_UNITS_PER_MAJOR),
        currency_code=currency_code,
    )


def build_price_book(column: int) -> dict[PlanKey, tuple[Money, ...]]:
    """One column of the table as the plan registry reads it: per plan, every
    currency's price."""

    book: dict[PlanKey, tuple[Money, ...]] = {}
    for currency_code, plans in PRICE_TABLE.items():
        for plan_key, prices in plans.items():
            book[plan_key] = (
                *book.get(plan_key, ()),
                build_local_price(currency_code, prices[column]),
            )

    return book


LOCAL_MONTHLY_PRICE_BOOK: dict[PlanKey, tuple[Money, ...]] = build_price_book(
    MONTHLY_PRICE_COLUMN
)
# The DONE_FOR_YOU setup fee; SELF_SERVE is free in every currency.
LOCAL_SETUP_FEE_BOOK: dict[PlanKey, tuple[Money, ...]] = build_price_book(
    SETUP_FEE_COLUMN
)
LOCAL_ADDITIONAL_LOCATION_PRICE_BOOK: dict[PlanKey, tuple[Money, ...]] = (
    build_price_book(ADDITIONAL_LOCATION_COLUMN)
)
