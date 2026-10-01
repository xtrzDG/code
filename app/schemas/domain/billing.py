from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceStatus,
    PlanKey,
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


class SubscriptionDocument(BaseDocument):
    """Subscription of a business to a plan (concept table `subscriptions`)."""

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


class InvoiceDocument(BaseDocument):
    """Invoice for a service period (concept table `invoices`)."""

    id: InvoiceId = Field(default_factory=InvoiceId)
    business_id: BusinessId
    subscription_id: SubscriptionId | None = None
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
