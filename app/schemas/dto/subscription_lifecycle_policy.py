"""The rules of the subscription lifecycle: pause price and cap, offers, win-back."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.subscription_lifecycle import (
    CancellationReason,
    RetentionOfferKind,
    WinBackStage,
)
from app.schemas.typings.subscription_lifecycle.constrained_integers import (
    PauseMonthCount,
    PausePricePercent,
    PauseWindowMonths,
    SaveCreditPercent,
    WinBackDayOffset,
)


class SubscriptionLifecyclePolicy(ImmutableDTO):
    """
    A paused month costs `pause_price_percent` of the monthly price; a
    business pauses at most `max_pause_months` in any `pause_window_months`.
    The cancel dialog answers each reason with the first offer of its list
    that the business can take (`offers`); the one-time credit is
    `save_credit_percent` of a month of the plan. Win-back messages go out
    `win_back_days` after a cancellation, never later than
    `win_back_horizon_days` (a job that was down catches up only that far).
    """

    pause_price_percent: PausePricePercent
    max_pause_months: PauseMonthCount
    pause_window_months: PauseWindowMonths
    save_credit_percent: SaveCreditPercent
    offers: dict[CancellationReason, list[RetentionOfferKind]]
    win_back_days: dict[WinBackStage, WinBackDayOffset]
    win_back_horizon_days: WinBackDayOffset
