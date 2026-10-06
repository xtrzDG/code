"""Whether a business can pause its subscription now, from when and how long."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.billing import BillingPeriod, SubscriptionStatus
from app.schemas.constants.subscription_lifecycle import PauseUnavailableReason
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.subscription_events import SubscriptionEventDocument
from app.schemas.dto.subscription_lifecycle import PauseAvailability
from app.schemas.dto.subscription_lifecycle_policy import SubscriptionLifecyclePolicy
from app.schemas.typings.subscription_lifecycle.booleans import IsPauseEnabled
from app.schemas.typings.subscription_lifecycle.constrained_integers import (
    PausedMonthCount,
    PauseMonthsAllowed,
)
from app.use_cases.shared.billing_records import find_next_period_start
from app.utilities.billing.pause_allowance import (
    max_pause_months,
    months_paused_before,
)


def read_pause_availability(
    business: BusinessDocument,
    subscription: SubscriptionDocument | None,
    invoices: Sequence[InvoiceDocument],
    events: Sequence[SubscriptionEventDocument],
    policy: SubscriptionLifecyclePolicy,
    is_enabled: IsPauseEnabled,
) -> PauseAvailability:
    """
    A business pauses a paid monthly subscription from the end of what is
    paid, for whole months within the cap; never while a pause is
    scheduled or running, and only once the platform turned pausing on.
    """

    reason: PauseUnavailableReason | None = None
    starts_at: Microseconds | None = None
    max_months: int = 0
    paused: int = 0
    if subscription is not None and subscription.status is SubscriptionStatus.ACTIVE:
        starts_at = find_next_period_start(subscription, list(invoices))
        paused = months_paused_before(
            events, starts_at, business.timezone, int(policy.pause_window_months)
        )
        max_months = max_pause_months(
            events,
            starts_at,
            business.timezone,
            int(policy.max_pause_months),
            int(policy.pause_window_months),
        )

    if not is_enabled:
        reason = PauseUnavailableReason.FEATURE_OFF
    elif subscription is not None and (
        subscription.status is SubscriptionStatus.PAUSED
        or subscription.pause_starts_at is not None
    ):
        reason = PauseUnavailableReason.ALREADY_PAUSED
    elif subscription is None or subscription.status is not SubscriptionStatus.ACTIVE:
        reason = PauseUnavailableReason.NOT_ACTIVE
    elif subscription.billing_period is not BillingPeriod.MONTHLY:
        reason = PauseUnavailableReason.NOT_MONTHLY
    elif max_months == 0:
        reason = PauseUnavailableReason.ALLOWANCE_USED

    return PauseAvailability(
        is_enabled=is_enabled,
        unavailable_reason=reason,
        starts_at=starts_at,
        max_months=PauseMonthsAllowed(max_months if reason is None else 0),
        paused_months=PausedMonthCount(paused),
    )
