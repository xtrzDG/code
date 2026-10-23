"""
What saving a card starts: when its first automatic charge is due, what
the charges are called on the provider's page (in the reader's language),
and the trial's one-time setup fee the card's page pays now.
"""

from typed_time_provider import Microseconds

from app.contracts.invoicing import InvoiceIssuingFacilitatorContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SetupOption,
    SubscriptionStatus,
)
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.dto.billing_ledger import InvoiceDescriptionInput
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.shared.billing_records import (
    list_open_invoices,
    sum_invoice_amounts,
)
from app.use_cases.shared.brand_billing import is_setup_fee_covered
from app.use_cases.shared.setup_fee_rules import is_setup_fee_pending
from app.use_cases.shared.subscription_pricing import price_setup_fee
from app.utilities.billing.billing_periods import add_billing_period

# Service periods that still count: paid ahead, declined, or billed.
COUNTED_PERIOD_STATUSES: frozenset[InvoiceStatus] = frozenset(
    {InvoiceStatus.PAID, InvoiceStatus.FAILED, InvoiceStatus.ISSUED}
)


def find_first_charge_at(
    subscription: SubscriptionDocument,
    invoices: list[InvoiceDocument],
    now: Microseconds,
) -> Microseconds:
    """
    When the new card is first charged automatically (never in the past):
    the trial's end; otherwise the end of the latest service period
    already billed (paid ahead, or declined and being retried, which the
    retries charge the new card for).
    """

    if (
        subscription.status is SubscriptionStatus.TRIALING
        and subscription.trial_ends_at is not None
    ):
        return max(subscription.trial_ends_at, now)

    billed_ends: list[Microseconds] = [
        invoice.period_end
        for invoice in invoices
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
        and invoice.status in COUNTED_PERIOD_STATUSES
    ]
    return max([subscription.period_end, now, *billed_ends])


def describe_charges(
    transformer: TransformerContract[InvoiceDescriptionInput, InvoiceDescription],
    plan_registry: PlanRegistryContract,
    business: BusinessDocument,
    subscription: SubscriptionDocument,
    language: LanguageTag,
    starts_at: Microseconds,
) -> InvoiceDescription:
    """
    The automatic charges named like the invoice of the first period they
    pay ("Call and message handling service — Voice + chat, monthly, …"),
    in the language of the provider's page.
    """

    plan: PlanDefinition = plan_registry.get(subscription.plan_key)
    return transformer.transform(
        InvoiceDescriptionInput(
            kind=InvoiceKind.SERVICE_PERIOD,
            language=language,
            timezone=business.timezone,
            plan_names=plan.names,
            billing_period=subscription.billing_period,
            period_start=starts_at,
            period_end=add_billing_period(
                starts_at, subscription.billing_period, business.timezone
            ),
        )
    )


def list_open_setup_fees(invoices: list[InvoiceDocument]) -> list[InvoiceDocument]:
    """The trial's setup fee billed and not paid yet (a card's page pays it)."""

    return [
        invoice
        for invoice in list_open_invoices(invoices)
        if invoice.kind is InvoiceKind.SETUP_FEE
    ]


def quote_setup_fee_due(
    plan_registry: PlanRegistryContract,
    invoice_issuing: InvoiceIssuingFacilitatorContract,
    brand_repo: BrandRepoContract,
    business_repo: BusinessRepoContract,
    business: BusinessDocument,
    subscription: SubscriptionDocument | None,
    business_invoices: list[InvoiceDocument],
) -> Money | None:
    """
    What saving a card in the trial charges now (with tax): the one-time
    setup fee of a business the platform team sets up, which a trial
    without a card is billed when it ends. Nothing outside a trial, for a
    self-serve setup, or once the fee is invoiced, waived or covered by
    another location of the brand.
    """

    if subscription is None or subscription.status is not SubscriptionStatus.TRIALING:
        return None

    open_fees: list[InvoiceDocument] = list_open_setup_fees(
        [
            invoice
            for invoice in business_invoices
            if invoice.subscription_id == subscription.id
        ]
    )
    if open_fees != []:
        return sum_invoice_amounts(open_fees)

    if not is_setup_fee_pending(subscription, business_invoices) or (
        is_setup_fee_covered(brand_repo, business_repo, business)
    ):
        return None

    return invoice_issuing.price_with_tax(
        business,
        price_setup_fee(
            plan_registry,
            subscription.plan_key,
            subscription.currency_code,
            SetupOption.DONE_FOR_YOU,
        ),
    ).total
