"""
What a paused month and the one-time save credit cost: shares of the
plan's monthly price, rounded half up to whole minor units.
"""

from app.schemas.constants.billing import BillingPeriod
from app.schemas.domain.billing import SubscriptionDocument

MONTHS_PER_YEAR: int = 12
PERCENT: int = 100


def monthly_price_minor(subscription: SubscriptionDocument) -> int:
    """The subscription's price per month (an annual price over twelve)."""

    price: int = int(subscription.price_minor)
    if subscription.billing_period is BillingPeriod.ANNUAL:
        return (price + MONTHS_PER_YEAR // 2) // MONTHS_PER_YEAR

    return price


def share_of_minor(amount_minor: int, percent: int) -> int:
    """`percent` of an amount, rounded half up to a whole minor unit."""

    return (amount_minor * percent + PERCENT // 2) // PERCENT


def pause_month_price_minor(subscription: SubscriptionDocument, percent: int) -> int:
    """What one paused month costs, before tax."""

    return share_of_minor(monthly_price_minor(subscription), percent)
