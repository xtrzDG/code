"""Cabinet billing: why owners cancel, what they are offered, the seasonal pause."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.subscription_lifecycle import (
    CancellationReason,
    PauseUnavailableReason,
    RetentionOfferKind,
)
from app.schemas.dto.catalog.plan_quotes import QuotedMoney
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.schemas.typings.subscription_lifecycle.booleans import (
    IsPauseAvailable,
    IsPauseEnabled,
)
from app.schemas.typings.subscription_lifecycle.constrained_integers import (
    PausedMonthCount,
    PauseMonthCount,
    PauseMonthsAllowed,
    PausePricePercent,
    PauseWindowMonths,
)
from app.schemas.typings.subscription_lifecycle.constrained_strings import (
    CancellationDetails,
)
from app.schemas.typings.users.prefixed_id import UserId


class CancelSubscriptionRequest(ImmutableDTO):
    """
    Body of a cancellation (optional): why, in the owner's words too, and
    the offer the dialog showed that they turned down.

    Example: {"reason": "seasonal_break", "details": "Closed until May",
    "declined_offer": "pause"}.
    """

    reason: CancellationReason | None = None
    details: CancellationDetails | None = None
    declined_offer: RetentionOfferKind | None = None


class PauseSubscriptionRequest(ImmutableDTO):
    """
    Body of a seasonal pause: how many whole months, from the end of the
    paid period.

    Example: {"months": 3}.
    """

    months: PauseMonthCount


class PauseSubscriptionCommand(ImmutableDTO):
    """Owner pauses the subscription for the season."""

    user_id: UserId
    business_id: BusinessId
    request: PauseSubscriptionRequest
    display_language: LanguageTag | None = None


class ResumeSubscriptionCommand(ImmutableDTO):
    """Owner calls off a scheduled pause or ends a running one."""

    user_id: UserId
    business_id: BusinessId
    display_language: LanguageTag | None = None


class AcceptRetentionOfferRequest(ImmutableDTO):
    """
    Body of an offer taken instead of cancelling: the reason the owner
    chose, the offer the dialog showed for it and, for a pause, its months.

    Example: {"reason": "too_expensive", "kind": "downgrade"}.
    """

    reason: CancellationReason
    kind: RetentionOfferKind
    pause_months: PauseMonthCount | None = None


class AcceptRetentionOfferCommand(ImmutableDTO):
    """Owner takes the offer the cancel dialog made."""

    user_id: UserId
    business_id: BusinessId
    request: AcceptRetentionOfferRequest
    display_language: LanguageTag | None = None


class SubscriptionLifecycleQuery(ImmutableDTO):
    """Owner opens the cancel dialog or the pause card."""

    user_id: UserId
    business_id: BusinessId
    display_language: LanguageTag | None = None


class PauseOptionsView(ImmutableDTO):
    """
    Whether the business can pause now and on what terms: from
    `starts_at` (the end of the paid period) for up to `max_months`
    months at `monthly_price` a month (`price_percent` of the plan);
    `paused_months` of the `cap_months` allowed in any `window_months` are
    used. `unavailable_reason` says why not when it cannot.
    """

    is_enabled: IsPauseEnabled
    is_available: IsPauseAvailable
    unavailable_reason: PauseUnavailableReason | None = None
    price_percent: PausePricePercent
    monthly_price: QuotedMoney | None = None
    starts_at: Microseconds | None = None
    max_months: PauseMonthsAllowed
    paused_months: PausedMonthCount
    cap_months: PauseMonthCount
    window_months: PauseWindowMonths


class RetentionOfferView(ImmutableDTO):
    """
    An offer instead of cancelling: a PAUSE of up to `pause_months`, a
    DOWNGRADE to `plan_key` at `plan_price`, or a one-time `credit`.
    """

    kind: RetentionOfferKind
    pause_months: PauseMonthsAllowed | None = None
    pause_price: QuotedMoney | None = None
    plan_key: PlanKey | None = None
    plan_name: LocalizedTextValue | None = None
    plan_price: QuotedMoney | None = None
    credit: QuotedMoney | None = None


class CancellationOfferView(ImmutableDTO):
    """What the dialog offers for one reason (None: nothing to offer)."""

    reason: CancellationReason
    offer: RetentionOfferView | None = None


class SubscriptionLifecycleView(ImmutableDTO):
    """
    The cancel dialog's reasons with their offers, in the order shown, and
    the pause card.
    """

    business_id: BusinessId
    pause: PauseOptionsView
    offers: list[CancellationOfferView] = Field(
        default_factory=list[CancellationOfferView]
    )


class PauseAvailability(ImmutableDTO):
    """
    Whether the business can pause now (`unavailable_reason` None), from
    when (`starts_at`, the end of what is paid) and for how many months at
    most; `paused_months` already paused in the window before then.
    """

    is_enabled: IsPauseEnabled
    unavailable_reason: PauseUnavailableReason | None = None
    starts_at: Microseconds | None = None
    max_months: PauseMonthsAllowed
    paused_months: PausedMonthCount
