"""Product events of the metric tests, written by hand at chosen moments."""

from typed_time_provider import Microseconds

from app.schemas.constants.analytics import (
    ProductEventName,
    ProductEventSource,
    TunnelStepKey,
)
from app.schemas.domain.product_events import (
    ProductEventDocument,
    ProductEventProperties,
)
from app.schemas.typings.analytics.constrained_integers import (
    MonthlyRecurringAmountMinor,
)
from app.schemas.typings.analytics.prefixed_id import ProductEventId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.users.prefixed_id import UserId

DAY: int = 24 * 60 * 60 * 1_000_000
# 2026-09-01T00:00:00Z: the first microsecond of September 2026.
SEPTEMBER: int = 1_788_220_800_000_000
EUR: CurrencyCode = CurrencyCode("EUR")
GEL: CurrencyCode = CurrencyCode("GEL")


def at_day(day: float) -> Microseconds:
    """A moment `day` days after 2026-09-01 00:00 UTC."""

    return Microseconds(SEPTEMBER + int(day * DAY))


def event(
    name: ProductEventName,
    day: float,
    business_id: BusinessId | None = None,
    user_id: UserId | None = None,
    properties: ProductEventProperties | None = None,
) -> ProductEventDocument:
    moment: Microseconds = at_day(day)
    return ProductEventDocument(
        id=ProductEventId(),
        name=name,
        occurred_at=moment,
        source=ProductEventSource.SERVER,
        user_id=user_id,
        business_id=business_id,
        properties=properties or ProductEventProperties(),
        created_at=moment,
        updated_at=moment,
    )


def billing(
    name: ProductEventName,
    day: float,
    business_id: BusinessId,
    amount: int = 0,
    currency: CurrencyCode = EUR,
) -> ProductEventDocument:
    """A billing step: what the subscription brings a month after it."""

    return event(
        name,
        day,
        business_id=business_id,
        properties=ProductEventProperties(
            monthly_amount=MonthlyRecurringAmountMinor(amount),
            currency_code=currency,
        ),
    )


def tunnel(
    name: ProductEventName, day: float, user_id: UserId, step: TunnelStepKey
) -> ProductEventDocument:
    return event(
        name,
        day,
        user_id=user_id,
        properties=ProductEventProperties(tunnel_step=step),
    )


def euro_cents_at_two_gel_per_euro(amount: int, currency: CurrencyCode) -> int | None:
    """A converter with one official rate (2 GEL a euro); others have none."""

    if currency == EUR:
        return amount
    if currency == GEL:
        return amount // 2
    return None
