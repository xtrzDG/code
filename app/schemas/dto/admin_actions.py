"""
The platform admin acts on a client's account (R13): a longer trial, a
discount, credit, a waived setup fee, an invoice paid by bank transfer or
in cash, a plan set by hand, the done-for-you setup marked done. Every
change carries the admin's reason into the audit log.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.billing import BillingPeriod, ManualPaymentMethod, PlanKey
from app.schemas.constants.compliance import AuditAction
from app.schemas.dto.billing import Money
from app.schemas.typings.access.constrained_strings import AdminActionReason
from app.schemas.typings.billing.booleans import (
    IsClientDiscountActive,
    IsSetupFeeWaived,
)
from app.schemas.typings.billing.constrained_integers import (
    BillingCreditAmountMinor,
    ClientDiscountPercent,
    TrialExtensionDays,
)
from app.schemas.typings.billing.constrained_strings import (
    DiscountEndDate,
    ManualPaymentReference,
)
from app.schemas.typings.billing.prefixed_id import InvoiceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.prefixed_id import AuditLogEntryId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.prefixed_id import UserId


class ExtendTrialBody(ImmutableDTO):
    """POST …/trial-extension: `days` more of the free trial, and why."""

    days: TrialExtensionDays
    reason: AdminActionReason


class GiveDiscountBody(ImmutableDTO):
    """
    POST …/discount: `percent` off every service period that starts on or
    before `last_day` (in the business's time zone); replaces an earlier
    discount.
    """

    percent: ClientDiscountPercent
    last_day: DiscountEndDate
    reason: AdminActionReason


class GrantCreditBody(ImmutableDTO):
    """
    POST …/credits: credit in minor units of the subscription's currency,
    taken off the price of the next invoices before tax.
    """

    amount_minor: BillingCreditAmountMinor
    reason: AdminActionReason


class AdminReasonBody(ImmutableDTO):
    """An action that needs nothing but the admin's reason (a waived fee)."""

    reason: AdminActionReason


class MarkInvoicePaidBody(ImmutableDTO):
    """POST …/invoices/{invoice_id}/manual-payment: money that came by hand."""

    method: ManualPaymentMethod
    reference: ManualPaymentReference
    reason: AdminActionReason


class OverridePlanBody(ImmutableDTO):
    """
    POST …/plan: the plan (and billing period; the current one when left
    out) the client is billed for from its next invoice, at the price book's
    price, without a checkout.
    """

    plan_key: PlanKey
    billing_period: BillingPeriod | None = None
    reason: AdminActionReason


class ExtendTrialCommand(ImmutableDTO):
    """A platform admin gives the client more days of its free trial."""

    user_id: UserId
    business_id: BusinessId
    body: ExtendTrialBody
    client_ip_address: ClientIpAddress | None = None


class GiveDiscountCommand(ImmutableDTO):
    """A platform admin gives the client a discount until a day."""

    user_id: UserId
    business_id: BusinessId
    body: GiveDiscountBody
    client_ip_address: ClientIpAddress | None = None


class GrantCreditCommand(ImmutableDTO):
    """A platform admin grants the client credit."""

    user_id: UserId
    business_id: BusinessId
    body: GrantCreditBody
    client_ip_address: ClientIpAddress | None = None


class WaiveSetupFeeCommand(ImmutableDTO):
    """A platform admin waives the client's setup fee."""

    user_id: UserId
    business_id: BusinessId
    body: AdminReasonBody
    client_ip_address: ClientIpAddress | None = None


class OverridePlanCommand(ImmutableDTO):
    """A platform admin sets the client's plan by hand."""

    user_id: UserId
    business_id: BusinessId
    body: OverridePlanBody
    client_ip_address: ClientIpAddress | None = None


class MarkInvoicePaidCommand(ImmutableDTO):
    """A platform admin records the payment of one of the client's invoices."""

    user_id: UserId
    business_id: BusinessId
    invoice_id: InvoiceId
    body: MarkInvoicePaidBody
    client_ip_address: ClientIpAddress | None = None


class CompleteOnboardingCommand(ImmutableDTO):
    """The platform team finished the done-for-you setup it was asked for."""

    user_id: UserId
    business_id: BusinessId
    client_ip_address: ClientIpAddress | None = None


class AdminActionReceipt(ImmutableDTO):
    """What an account action recorded: the audit entry and when."""

    business_id: BusinessId
    action: AuditAction
    audit_log_entry_id: AuditLogEntryId
    occurred_at: Microseconds


class ClientDiscountView(ImmutableDTO):
    """The client's discount: percent off periods starting before `ends_at`."""

    percent: ClientDiscountPercent
    ends_at: Microseconds
    is_active: IsClientDiscountActive


class ClientAccountView(ImmutableDTO):
    """
    What the platform team granted the client, for the actions menu: the
    trial's end, the discount, the credit left (in the subscription's
    currency) and whether the setup fee is waived.
    """

    trial_ends_at: Microseconds | None = None
    discount: ClientDiscountView | None = None
    credit_balance: Money | None = None
    is_setup_fee_waived: IsSetupFeeWaived = False
