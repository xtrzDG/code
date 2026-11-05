"""
What one booking (or order) of each niche typically brings, and how long
staff take to answer a customer, for the value estimates of businesses
whose owner has not given their own average check yet.

Typical checks are in euro (a whole booking: a table for the party, a
stay, a service, a lesson), converted into a business's currency only
with an official rate (`ExchangeRateRegistry`); niches whose checks vary
too much to guess (real estate, B2B supply) have none, so their owners
see counts until they give their own. Every estimate is shown as one, and
the owner can correct the check inline.

Staff time: a written reply takes 60 to 120 seconds (reading the question,
looking up the answer, typing it); an answered call 3 to 6 minutes
(longer where calls are consultations).
"""

from app.schemas.constants.niches import NicheKey
from app.schemas.dto.billing import Money
from app.schemas.dto.value.niche_value import NicheValueDefaults
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.value.constrained_integers import (
    StaffSecondsPerCall,
    StaffSecondsPerReply,
)

EURO: CurrencyCode = CurrencyCode("EUR")


def _defaults(
    niche_key: NicheKey,
    typical_check_euro: int | None,
    seconds_per_reply: int,
    seconds_per_call: int,
) -> NicheValueDefaults:
    return NicheValueDefaults(
        niche_key=niche_key,
        typical_check=(
            None
            if typical_check_euro is None
            else Money(
                amount_minor=MoneyAmountMinor(typical_check_euro * 100),
                currency_code=EURO,
            )
        ),
        seconds_per_reply=StaffSecondsPerReply(seconds_per_reply),
        seconds_per_call=StaffSecondsPerCall(seconds_per_call),
    )


NICHE_VALUE_DEFAULTS: tuple[NicheValueDefaults, ...] = (
    _defaults(NicheKey.RESTAURANT, 40, 75, 180),
    _defaults(NicheKey.HOTEL, 120, 105, 300),
    _defaults(NicheKey.ENTERTAINMENT, 35, 75, 180),
    _defaults(NicheKey.BEAUTY_SALON, 30, 75, 180),
    _defaults(NicheKey.CLINIC, 50, 105, 300),
    _defaults(NicheKey.FITNESS, 20, 75, 180),
    _defaults(NicheKey.SHORT_TERM_RENTAL, 150, 105, 240),
    _defaults(NicheKey.CAR_SERVICE, 80, 90, 240),
    _defaults(NicheKey.CAR_RENTAL_AND_TOURS, 100, 105, 300),
    _defaults(NicheKey.EVENT_VENUE, 600, 120, 360),
    _defaults(NicheKey.REAL_ESTATE, None, 120, 360),
    _defaults(NicheKey.EDUCATION, 25, 90, 240),
    _defaults(NicheKey.ONLINE_SHOP, 35, 75, 180),
    _defaults(NicheKey.VETERINARY, 40, 90, 240),
    _defaults(NicheKey.HOME_SERVICES, 60, 90, 240),
    _defaults(NicheKey.B2B_SUPPLY, None, 120, 300),
)
