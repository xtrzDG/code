"""Internal billing DTOs: issuing invoices, usage totals, cost and notices."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.billing import (
    BillingNoticeKind,
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    PackageMetric,
    UsageKind,
)
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.catalog import ExchangeRateQuote
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.billing.booleans import IsSetupFeeIncluded
from app.schemas.typings.billing.constrained_floats import GrossMarginPercent
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    IncludedDialogs,
    IncludedVoiceMinutes,
    PackageUsagePercent,
    UsageQuantityTotal,
    UsedDialogs,
    UsedVoiceMinutes,
)
from app.schemas.typings.billing.integers import MarginAmountMinor
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)


class DueInvoicesRequest(ImmutableDTO):
    """
    Issue the invoice of the service period starting at `period_start` (and
    the one-time setup fee when included and not invoiced yet).

    `status` is ISSUED for a bill to pay, PAID for an automatic charge that
    already succeeded, FAILED for one that was declined.
    """

    business: BusinessDocument
    subscription: SubscriptionDocument
    period_start: Microseconds
    status: InvoiceStatus = InvoiceStatus.ISSUED
    payment_reference: PaymentProviderReference | None = None
    is_setup_fee_included: IsSetupFeeIncluded = False


class InvoiceDescriptionInput(ImmutableDTO):
    """What an invoice line says, in the reader's language."""

    kind: InvoiceKind
    language: LanguageTag
    timezone: TimezoneName
    plan_names: LocalizedText
    billing_period: BillingPeriod
    period_start: Microseconds
    period_end: Microseconds


class PackageUsageTotals(ImmutableDTO):
    """Metered package use of one business in one window."""

    period_start: Microseconds
    period_end: Microseconds
    used_voice_minutes: UsedVoiceMinutes
    used_dialogs: UsedDialogs


class UsageCostLine(ImmutableDTO):
    """Usage of one kind in a period with its provider cost."""

    kind: UsageKind
    quantity: UsageQuantityTotal
    cost_micro_usd: CostMicroUsd


class MarginMoney(ImmutableDTO):
    """Revenue minus provider cost; negative for a loss."""

    amount_minor: MarginAmountMinor
    currency_code: CurrencyCode


class ClientCostQuery(ImmutableDTO):
    """Provider cost and revenue of one business for [period_start, period_end)."""

    business_id: BusinessId
    period_start: Microseconds
    period_end: Microseconds


class ClientCostReport(ImmutableDTO):
    """
    What one client cost the platform and brought in for a period.

    Provider costs are in micro US dollars (provider price lists); revenue is
    the paid invoices of the period in the subscription currency, prorated
    by service time. The cost is converted with an official rate when the
    catalog has one; without it the money cost and the margin stay empty.
    """

    business_id: BusinessId
    period_start: Microseconds
    period_end: Microseconds
    usage_cost_lines: list[UsageCostLine] = Field(default_factory=list[UsageCostLine])
    llm_cost_micro_usd: CostMicroUsd
    provider_cost_micro_usd: CostMicroUsd
    revenue: Money
    provider_cost: Money | None = None
    margin: MarginMoney | None = None
    margin_percent: GrossMarginPercent | None = None
    exchange_rate: ExchangeRateQuote | None = None
    planned_monthly_provider_cost: Money | None = None


class BillingNotice(ImmutableDTO):
    """
    A billing message to the owners, rendered in `language`.

    Fields beyond the kind, language and business are filled per kind:
    `amount` and `deadline` for payment problems, the package fields for the
    usage warning.
    """

    kind: BillingNoticeKind
    language: LanguageTag
    timezone: TimezoneName
    business_name: BusinessName
    amount: Money | None = None
    deadline: Microseconds | None = None
    metric: PackageMetric | None = None
    usage_percent: PackageUsagePercent | None = None
    used_voice_minutes: UsedVoiceMinutes | None = None
    included_voice_minutes: IncludedVoiceMinutes | None = None
    used_dialogs: UsedDialogs | None = None
    included_dialogs: IncludedDialogs | None = None
    overage_price_per_minute: Money | None = None
