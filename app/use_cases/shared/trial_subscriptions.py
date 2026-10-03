"""
Opening the free trial, shared by the owner's "start trial" and the trial
that starts by itself when the assistant first goes live.
"""

from typed_time_provider import Microseconds

from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceStatus,
    PlanKey,
    SubscriptionStatus,
)
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.typings.billing.prefixed_id import SubscriptionId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.use_cases.shared.billing_records import (
    find_current_subscription,
    is_trial_available,
    list_open_invoices,
    list_subscription_invoices,
)
from app.use_cases.shared.subscription_pricing import (
    price_subscription,
    select_subscription_currency,
)
from app.utilities.billing.billing_periods import add_local_days


def is_trial_due_at_go_live(
    subscriptions: list[SubscriptionDocument],
    plan: PlanDefinition,
) -> bool:
    """
    The trial starts when the assistant goes live: it is still available
    (once per business) and the plan has one.
    """

    return is_trial_available(subscriptions) and int(plan.trial_days) > 0


def choose_go_live_trial(
    business: BusinessDocument,
    current: SubscriptionDocument | None,
) -> tuple[PlanKey, BillingPeriod]:
    """
    The plan and billing period of a trial starting at go-live: those of a
    subscription chosen without a trial and never paid, else the business
    plan billed monthly.
    """

    if current is not None and current.status is SubscriptionStatus.INCOMPLETE:
        return current.plan_key, current.billing_period

    return business.plan_key, BillingPeriod.MONTHLY


def open_trial_subscription(
    subscription_repo: SubscriptionRepoContract,
    invoice_repo: InvoiceRepoContract,
    plan_registry: PlanRegistryContract,
    business: BusinessDocument,
    plan_key: PlanKey,
    billing_period: BillingPeriod,
    now: Microseconds,
) -> SubscriptionDocument:
    """
    Store the TRIALING subscription that runs until the plan's trial days
    end in the business time zone, priced in the business currency when the
    price book has it (else EUR); nothing is invoiced. A subscription chosen
    without a trial and never paid (INCOMPLETE) becomes the trial: its
    unpaid bills are voided. The caller checks that the trial is due.
    """

    plan: PlanDefinition = plan_registry.get(plan_key)
    currency_code: CurrencyCode = select_subscription_currency(
        plan_registry, plan_key, business.currency_code
    )
    price: Money = price_subscription(
        plan_registry, plan_key, billing_period, currency_code
    )
    trial_ends_at: Microseconds = add_local_days(
        now, int(plan.trial_days), business.timezone
    )
    unpaid: SubscriptionDocument | None = find_current_subscription(
        subscription_repo, business.id
    )
    if unpaid is not None:
        void_unpaid_invoices(invoice_repo, unpaid, now)

    subscription = SubscriptionDocument(
        id=SubscriptionId() if unpaid is None else unpaid.id,
        business_id=business.id,
        plan_key=plan_key,
        billing_period=billing_period,
        price_minor=price.amount_minor,
        currency_code=price.currency_code,
        status=SubscriptionStatus.TRIALING,
        trial_ends_at=trial_ends_at,
        period_start=now,
        period_end=trial_ends_at,
        created_at=now if unpaid is None else unpaid.created_at,
        updated_at=now,
    )
    subscription_repo.save(subscription)
    return subscription


def void_unpaid_invoices(
    invoice_repo: InvoiceRepoContract,
    subscription: SubscriptionDocument,
    now: Microseconds,
) -> None:
    """Void the open bills of a subscription the free trial now covers."""

    open_invoices: list[InvoiceDocument] = list_open_invoices(
        list_subscription_invoices(invoice_repo, subscription)
    )
    for invoice in open_invoices:
        invoice.status = InvoiceStatus.VOID
        invoice.updated_at = now
        invoice_repo.save(invoice)
