from app.contracts.subscription_lifecycle import (
    SubscriptionLifecyclePolicyRegistryContract,
)
from app.schemas.constants.subscription_lifecycle import (
    CancellationReason,
    RetentionOfferKind,
    WinBackStage,
)
from app.schemas.dto.subscription_lifecycle_policy import SubscriptionLifecyclePolicy
from app.schemas.typings.subscription_lifecycle.constrained_integers import (
    PauseMonthCount,
    PausePricePercent,
    PauseWindowMonths,
    SaveCreditPercent,
    WinBackDayOffset,
)

PAUSE = RetentionOfferKind.PAUSE
DOWNGRADE = RetentionOfferKind.DOWNGRADE
CREDIT = RetentionOfferKind.CREDIT

# What the cancel dialog offers for each reason, best first; the first
# one the business can take is shown. Closing the business gets nothing:
# an owner who is closing is let go without a sales pitch.
OFFERS_BY_REASON: dict[CancellationReason, list[RetentionOfferKind]] = {
    CancellationReason.TOO_EXPENSIVE: [DOWNGRADE, PAUSE, CREDIT],
    CancellationReason.SEASONAL_BREAK: [PAUSE],
    CancellationReason.NOT_ENOUGH_USE: [PAUSE, DOWNGRADE],
    CancellationReason.MISSING_FEATURE: [CREDIT],
    CancellationReason.ANSWER_QUALITY: [CREDIT],
    CancellationReason.SWITCHED_PROVIDER: [CREDIT],
    CancellationReason.CLOSING_BUSINESS: [],
    CancellationReason.OTHER: [PAUSE],
}


class SubscriptionLifecyclePolicyRegistry(SubscriptionLifecyclePolicyRegistryContract):
    """
    The platform's lifecycle rules (concept: seasonal businesses pause
    instead of churning):

    - a paused month costs 15% of the plan's monthly price, and a business
      pauses at most 4 months in any 12;
    - the one-time credit is half a month of the plan;
    - win-back messages go out 14 and 30 days after a cancellation, and
      not later than 45 days after it.
    """

    def policy(self) -> SubscriptionLifecyclePolicy:
        return SubscriptionLifecyclePolicy(
            pause_price_percent=PausePricePercent(15),
            max_pause_months=PauseMonthCount(4),
            pause_window_months=PauseWindowMonths(12),
            save_credit_percent=SaveCreditPercent(50),
            offers={
                reason: list(offers) for reason, offers in OFFERS_BY_REASON.items()
            },
            win_back_days={
                WinBackStage.DAY_14: WinBackDayOffset(14),
                WinBackStage.DAY_30: WinBackDayOffset(30),
            },
            win_back_horizon_days=WinBackDayOffset(45),
        )
