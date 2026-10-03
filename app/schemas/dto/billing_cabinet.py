"""Cabinet billing: trial, plan, cancellation, checkout and the overview page."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    PlanKey,
    SetupOption,
    SubscriptionStatus,
)
from app.schemas.constants.businesses import ServiceMode
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.catalog.plan_quotes import QuotedMoney
from app.schemas.typings.billing.booleans import (
    IsAutoDebitActive,
    IsSubscriptionCreated,
    IsTrialAvailable,
    IsTrialStartingAtGoLive,
)
from app.schemas.typings.billing.constrained_integers import (
    IncludedDialogs,
    IncludedVoiceMinutes,
    OverageVoiceMinutes,
    PackageUsagePercent,
    UsedDialogs,
    UsedVoiceMinutes,
)
from app.schemas.typings.billing.constrained_strings import (
    PaymentCheckoutUrl,
    PaymentReturnUrl,
)
from app.schemas.typings.billing.prefixed_id import (
    InvoiceId,
    PaymentOrderId,
    SubscriptionId,
)
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.schemas.typings.users.prefixed_id import UserId


class StartTrialRequest(ImmutableDTO):
    """
    Body of the trial request; the plan defaults to the business plan.

    Example: {"plan_key": "voice_and_chat", "billing_period": "monthly"}.
    """

    plan_key: PlanKey | None = None
    billing_period: BillingPeriod = BillingPeriod.MONTHLY


class StartTrialCommand(ImmutableDTO):
    """Owner starts the free trial of a business (once per business)."""

    user_id: UserId
    business_id: BusinessId
    request: StartTrialRequest
    display_language: LanguageTag | None = None


class ChangePlanRequest(ImmutableDTO):
    """
    Body of the plan change.

    Example: {"plan_key": "plus", "billing_period": "annual"}.
    """

    plan_key: PlanKey
    billing_period: BillingPeriod


class ChangePlanCommand(ImmutableDTO):
    """Owner switches plan or billing period."""

    user_id: UserId
    business_id: BusinessId
    request: ChangePlanRequest
    display_language: LanguageTag | None = None


class CancelSubscriptionCommand(ImmutableDTO):
    """Owner cancels the subscription at the end of the paid period."""

    user_id: UserId
    business_id: BusinessId
    display_language: LanguageTag | None = None


class StartCheckoutRequest(ImmutableDTO):
    """
    Body of the checkout request. `return_url` must be a page of an allowed
    cabinet origin; the payer's browser returns there after paying.

    Example: {"return_url": "https://app.example.com/billing"}.
    """

    return_url: PaymentReturnUrl | None = None


class StartCheckoutCommand(ImmutableDTO):
    """Owner pays the open invoices and turns on automatic charges."""

    user_id: UserId
    business_id: BusinessId
    request: StartCheckoutRequest
    display_language: LanguageTag | None = None


class SubscribeRequest(ImmutableDTO):
    """
    Body of a subscription paid now: the plan and billing period to pay
    for, how the business is set up (SELF_SERVE, free; DONE_FOR_YOU, the
    platform team sets it up for the plan's setup fee), and the cabinet
    page to return to (as in the checkout request).

    Example: {"plan_key": "chat", "billing_period": "annual",
    "setup_option": "self_serve",
    "return_url": "https://app.example.com/b/bus_1/billing"}.
    """

    plan_key: PlanKey
    billing_period: BillingPeriod = BillingPeriod.MONTHLY
    setup_option: SetupOption = SetupOption.SELF_SERVE
    return_url: PaymentReturnUrl | None = None


class SubscribeCommand(ImmutableDTO):
    """Owner subscribes to a plan and goes to the payment page."""

    user_id: UserId
    business_id: BusinessId
    request: SubscribeRequest
    display_language: LanguageTag | None = None


class SetupOptionChoice(ImmutableDTO):
    """An owner's setup option for the subscription about to be paid."""

    user_id: UserId
    business: BusinessDocument
    subscription_id: SubscriptionId
    option: SetupOption


class SubscriptionOpening(ImmutableDTO):
    """
    The subscription a payment will be for; `is_created` when it was just
    opened (waiting for its first payment) rather than already there.
    """

    subscription_id: SubscriptionId
    is_created: IsSubscriptionCreated


class BillingOverviewQuery(ImmutableDTO):
    """Owner opens the billing page; language defaults to the owner language."""

    user_id: UserId
    business_id: BusinessId
    display_language: LanguageTag | None = None


class BillingOverviewSource(ImmutableDTO):
    """An authorized business whose billing page should be assembled."""

    business: BusinessDocument
    display_language: LanguageTag | None = None


class SubscriptionView(ImmutableDTO):
    """
    The subscription as the billing page shows it; `setup_option` is how
    the business is set up (None: chosen before the choice existed, free),
    `onboarding_requested_at` when the owner asked the platform team to set
    it up.
    """

    id: SubscriptionId
    plan_key: PlanKey
    plan_name: LocalizedTextValue
    billing_period: BillingPeriod
    status: SubscriptionStatus
    price: QuotedMoney
    trial_ends_at: Microseconds | None = None
    period_start: Microseconds
    period_end: Microseconds
    grace_until: Microseconds | None = None
    has_auto_debit: IsAutoDebitActive
    setup_option: SetupOption | None = None
    onboarding_requested_at: Microseconds | None = None


class PackageUsageView(ImmutableDTO):
    """
    Use of the plan package in the current billing period.

    Percents are empty for a package of zero (the Chat plan has no minutes).
    Overage is priced in the subscription currency when an official rate
    allows it (then marked estimated), otherwise in the plan currency.
    """

    period_start: Microseconds
    period_end: Microseconds
    used_voice_minutes: UsedVoiceMinutes
    included_voice_minutes: IncludedVoiceMinutes
    voice_usage_percent: PackageUsagePercent | None = None
    used_dialogs: UsedDialogs
    included_dialogs: IncludedDialogs
    dialog_usage_percent: PackageUsagePercent | None = None
    overage_voice_minutes: OverageVoiceMinutes
    overage_price_per_minute: QuotedMoney
    overage_cost: QuotedMoney


class InvoiceView(ImmutableDTO):
    """One invoice with its amount formatted for the reader."""

    id: InvoiceId
    kind: InvoiceKind
    description: InvoiceDescription
    amount: QuotedMoney
    status: InvoiceStatus
    period_start: Microseconds
    period_end: Microseconds
    issued_at: Microseconds


class BillingOverview(ImmutableDTO):
    """
    The billing page: plan, status, period, package usage and invoices.

    `does_trial_start_at_go_live` is True while the business is not live
    yet and its free trial will start by itself when it goes live.
    """

    business_id: BusinessId
    display_language: LanguageTag
    currency_code: CurrencyCode
    service_mode: ServiceMode
    is_trial_available: IsTrialAvailable
    does_trial_start_at_go_live: IsTrialStartingAtGoLive = False
    subscription: SubscriptionView | None = None
    usage: PackageUsageView | None = None
    invoices: list[InvoiceView] = Field(default_factory=list[InvoiceView])


class CheckoutSessionView(ImmutableDTO):
    """Hosted payment page for the open invoices."""

    payment_order_id: PaymentOrderId
    checkout_url: PaymentCheckoutUrl
    amount: QuotedMoney
    invoice_ids: list[InvoiceId]
