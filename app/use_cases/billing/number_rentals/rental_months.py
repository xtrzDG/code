"""
The months of a rented number and what each one becomes when it begins.

Months run from the moment the number was taken, in the business's time
zone: the k-th month starts k calendar months after `rented_at` (the day
clamped to the month's length, counted from the rental day each time, so
a number taken on the 31st never drifts to the 28th for good).
"""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.constants.phone_numbers import RentalMonthOutcome
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.phone_numbers import PhoneNumberDocument
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.utilities.billing.billing_periods import add_calendar_months

# A paying customer: the month goes on the subscription's bill (PAST_DUE
# only while its grace lasts, `_is_paying`).
BILLED_STATUSES: frozenset[SubscriptionStatus] = frozenset(
    {
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.PAST_DUE,
        SubscriptionStatus.PAUSED,
    }
)
# More months than any rental lasts (a hundred years): the search's bound.
MONTHS_BOUND: int = 1_200


def month_bounds(
    number: PhoneNumberDocument, timezone: TimezoneName
) -> tuple[Microseconds, Microseconds]:
    """Start and end of the rental month that begins at `billed_until`."""

    for months in range(MONTHS_BOUND):
        start: Microseconds = add_calendar_months(number.rented_at, months, timezone)
        if start >= number.billed_until:
            return start, add_calendar_months(number.rented_at, months + 1, timezone)

    raise ValueError(f"Rented number {number.id} has no rental month left.")


def decide_rental_month(
    number: PhoneNumberDocument,
    subscription: SubscriptionDocument | None,
    month_start: Microseconds,
) -> RentalMonthOutcome:
    """
    What the month is, judged at its start (the job may settle it later,
    catching up). On the platform (INCLUDED): a month that begins in the
    trial, whatever the subscription became since. BILLED for a paying
    customer: active, paused, or past due while the grace lasts. On the
    platform as well: the first month of a number taken before the first
    payment, and the month that begins in a cancelled subscription's last
    paid period. Otherwise nobody pays for the service, a past due
    subscription whose grace ran out included, so the number goes back
    (RELEASED).
    """

    if subscription is not None and _begins_in_trial(subscription, month_start):
        return RentalMonthOutcome.INCLUDED

    if subscription is not None and _is_paying(subscription, month_start):
        return RentalMonthOutcome.BILLED

    if month_start <= number.rented_at:
        return RentalMonthOutcome.INCLUDED

    if subscription is None:
        return RentalMonthOutcome.RELEASED

    if (
        subscription.status is SubscriptionStatus.CANCELLED
        and month_start < subscription.period_end
    ):
        return RentalMonthOutcome.INCLUDED

    return RentalMonthOutcome.RELEASED


def _begins_in_trial(
    subscription: SubscriptionDocument, month_start: Microseconds
) -> bool:
    if subscription.trial_ends_at is None:
        return subscription.status is SubscriptionStatus.TRIALING

    return month_start < subscription.trial_ends_at


def _is_paying(subscription: SubscriptionDocument, month_start: Microseconds) -> bool:
    if subscription.status not in BILLED_STATUSES:
        return False

    if subscription.status is not SubscriptionStatus.PAST_DUE:
        return True

    return subscription.grace_until is None or month_start < subscription.grace_until
