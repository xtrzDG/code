from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    ManualPaymentMethod,
    OnboardingRequestStatus,
    PlanKey,
    SetupOption,
    SubscriptionStatus,
    UsageKind,
)
from app.schemas.constants.invoicing import TaxTreatment
from app.schemas.domain.billing_profiles import (
    InvoiceLineText,
    InvoiceParty,
    PaymentCardSnapshot,
)
from app.schemas.typings.billing.booleans import IsSetupFeeWaived
from app.schemas.typings.billing.constrained_integers import (
    ClientDiscountPercent,
    CostMicroUsd,
    MoneyAmountMinor,
    UsageQuantity,
)
from app.schemas.typings.billing.constrained_strings import ManualPaymentReference
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
from app.schemas.typings.invoicing.constrained_integers import TaxRateBasisPoints
from app.schemas.typings.invoicing.constrained_strings import InvoiceNumber
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.users.prefixed_id import UserId


class SubscriptionDiscount(PersistentDocument):
    """
    A discount a platform admin gave the client: `percent` off the price of
    every service period that starts before `ends_at` (the first moment
    after the last discounted day, in the business's time zone).
    """

    percent: ClientDiscountPercent
    ends_at: Microseconds
    granted_by: UserId
    granted_at: Microseconds


class SubscriptionDocument(BaseDocument):
    """
    Subscription of a business to a plan (concept table `subscriptions`).

    `setup_option` is how the business is set up: DONE_FOR_YOU brings the
    plan's setup fee with the first monthly invoice; SELF_SERVE, and None
    (a subscription from before the choice existed, or the trial that
    starts at go-live), is free.

    Version 2: `setup_option` (optional, so version 1 rows read as they are).
    Version 3: what the platform team granted (R13, optional): a
    `discount` on the service periods and `is_setup_fee_waived`, the
    setup fee no longer charged.
    Version 4: a seasonal pause (R14, optional): `pause_starts_at` (the end
    of the paid period, when the pause job makes it PAUSED) and
    `pause_until` (when the job resumes it); both None without a pause.
    """

    schema_version: SchemaVersion = SchemaVersion("4")
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
    discount: SubscriptionDiscount | None = None
    is_setup_fee_waived: IsSetupFeeWaived = False
    pause_starts_at: Microseconds | None = None
    pause_until: Microseconds | None = None


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


class ManualPayment(PersistentDocument):
    """
    Money for an invoice that came outside the payment provider, recorded by
    a platform admin: how (a bank transfer or cash), its reference, who
    recorded it and when.
    """

    method: ManualPaymentMethod
    reference: ManualPaymentReference
    recorded_by: UserId
    recorded_at: Microseconds


class InvoiceDocument(BaseDocument):
    """
    Invoice for a service period or the one-time setup fee (concept table
    `invoices`). A setup fee invoice has a zero-length period at its issue time.

    Version 2, the accountant's invoice: its `number` in the seller's
    yearly series, the `seller` and the `buyer` as they were when it was
    issued, the price before tax (`subtotal_minor`), the VAT rate, amount
    and treatment, and once paid when (`paid_at`) and with which card
    (masked). `amount_minor` stays what is charged: the total with tax.
    `description` is the line in the owner language as issued;
    `line_texts` words it in each language the PDFs are written in.
    All optional: an invoice of version 1 gets its number and parties when
    its PDF is first asked for, carries no tax, and prints `description`.

    Version 3 (R13, optional): what came off the price before tax, the
    client's `discount_percent` (`discount_minor`) and the credit it used
    (`credit_minor`), so `subtotal_minor` is the price minus both; and a
    payment a platform admin recorded by hand (`manual_payment`: a bank
    transfer or cash, with its reference).
    """

    schema_version: SchemaVersion = SchemaVersion("3")
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
    number: InvoiceNumber | None = None
    seller: InvoiceParty | None = None
    buyer: InvoiceParty | None = None
    subtotal_minor: MoneyAmountMinor | None = None
    tax_rate_basis_points: TaxRateBasisPoints | None = None
    tax_minor: MoneyAmountMinor | None = None
    tax_treatment: TaxTreatment | None = None
    paid_at: Microseconds | None = None
    payment_card: PaymentCardSnapshot | None = None
    line_texts: list[InvoiceLineText] = Field(default_factory=list[InvoiceLineText])
    discount_percent: ClientDiscountPercent | None = None
    discount_minor: MoneyAmountMinor | None = None
    credit_minor: MoneyAmountMinor | None = None
    manual_payment: ManualPayment | None = None


class UsageEventDocument(BaseDocument):
    """
    Metered usage with provider cost (concept table `usage_events`).

    Version 2: the kind `transcription_seconds` (voice notes transcribed).
    """

    schema_version: SchemaVersion = SchemaVersion("2")
    id: UsageEventId = Field(default_factory=UsageEventId)
    business_id: BusinessId
    conversation_id: ConversationId | None = None
    kind: UsageKind
    quantity: UsageQuantity
    cost_micro_usd: CostMicroUsd = CostMicroUsd(0)
    occurred_at: Microseconds
