"""The period a client's usage is summed over."""

from typed_time_provider import Microseconds

from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.utilities.billing.billing_periods import find_usage_window

MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000
NO_SUBSCRIPTION_WINDOW_DAYS: int = 30


def find_client_usage_window(
    business: BusinessDocument,
    subscription: SubscriptionDocument | None,
    now: Microseconds,
) -> tuple[Microseconds, Microseconds]:
    """The window usage is summed over: the billing window, else 30 days."""

    # A subscription still waiting for its first payment has an empty
    # period; it is metered like no subscription at all.
    if subscription is not None and subscription.period_end > subscription.period_start:
        return find_usage_window(subscription, now, business.timezone)

    return (
        Microseconds(int(now) - NO_SUBSCRIPTION_WINDOW_DAYS * MICROSECONDS_PER_DAY),
        Microseconds(int(now) + 1),
    )
