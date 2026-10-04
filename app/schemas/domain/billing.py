from base_pydantic_schemas import BaseDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    OnboardingRequestStatus,
    PlanKey,
    SetupOption,
    SubscriptionStatus,
    UsageKind,
)
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    MoneyAmountMinor,
    UsageQuantity,
)
from app.schemas.typings.billing.prefixed_id import (
    InvoiceId,
    OnboardingRequestId,
    SubscriptionId,
    UsageEventId,
)
from app.schemas.typings.billing.strings import (
    InvoiceDescription,
    PaymentProviderReference,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.users.prefixed_id import UserId


class SubscriptionDocument(BaseDocument):
    """
    Subscription of a business to a plan (concept table `subscriptions`).

    `setup_option` is how the business is set up: DONE_FOR_YOU brings the
    plan's setup fee with the first monthly invoice; SELF_SERVE, and None
    (a subscription from before the choice existed, or the trial that
    starts at go-live), is free.

    Version 2: `setup_option` (optional, so version 1 rows read as they are).
    """

    schema_version: SchemaVersion = SchemaVersion("2")
    id: SubscriptionId = Field(default_factory=SubscriptionId)
    business_id: BusinessId
    plan_key: PlanKey
    billing_period: BillingPeriod
    price_minor: MoneyAmountMinor
    currency_code: CurrencyCode
    status: SubscriptionStatus
    trial_ends_at: Microseconds | None = None
    period_start: Microseconds
    period_end: Microseconds
    grace_until: Microseconds | None = None
    provider_reference: PaymentProviderReference | None = None
    setup_option: SetupOption | None = None


class OnboardingRequestDocument(BaseDocument):
    """
    An owner asked the platform team to set the business up (the
    DONE_FOR_YOU setup option): who asked, for which plan, and whether the
    team is done. One per business (the id derives from it); the admin
    client page shows it and the platform admins get an e-mail.
    """

    id: OnboardingRequestId
    business_id: BusinessId
    requested_by: UserId
    plan_key: PlanKey
    status: OnboardingRequestStatus = OnboardingRequestStatus.OPEN
    requested_at: Microseconds


class InvoiceDocument(BaseDocument):
    """
    Invoice for a service period or the one-time setup fee (concept table
    `invoices`). A setup fee invoice has a zero-length period at its issue time.
    """

    id: InvoiceId = Field(default_factory=InvoiceId)
    business_id: BusinessId
    subscription_id: SubscriptionId | None = None
    kind: InvoiceKind = InvoiceKind.SERVICE_PERIOD
    description: InvoiceDescription
    amount_minor: MoneyAmountMinor
    currency_code: CurrencyCode
    status: InvoiceStatus = InvoiceStatus.ISSUED
    period_start: Microseconds
    period_end: Microseconds
    provider_reference: PaymentProviderReference | None = None


class UsageEventDocument(BaseDocument):
    """Metered usage with provider cost (concept table `usage_events`)."""

    id: UsageEventId = Field(default_factory=UsageEventId)
    business_id: BusinessId
    conversation_id: ConversationId | None = None
    kind: UsageKind
    quantity: UsageQuantity
    cost_micro_usd: CostMicroUsd = CostMicroUsd(0)
    occurred_at: Microseconds
