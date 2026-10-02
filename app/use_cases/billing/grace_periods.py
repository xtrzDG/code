"""When an unpaid subscription becomes past due, and until when it may pay."""

from typed_time_provider import Microseconds

from app.contracts.registries import PlanRegistryContract
from app.schemas.constants.billing import InvoiceKind, SubscriptionStatus
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import PlanDefinition
from app.use_cases.billing.billing_records import list_open_invoices
from app.utilities.billing.billing_periods import add_local_days


def start_grace_period(
    plan_registry: PlanRegistryContract,
    subscription: SubscriptionDocument,
    business: BusinessDocument,
    now: Microseconds,
) -> None:
    """Past due from now, with the plan's grace days (business-local) to pay."""

    plan: PlanDefinition = plan_registry.get(subscription.plan_key)
    subscription.status = SubscriptionStatus.PAST_DUE
    subscription.grace_until = add_local_days(
        now,
        int(plan.grace_period_days),
        business.timezone,
    )


def start_overage_grace(
    plan_registry: PlanRegistryContract,
    subscription: SubscriptionDocument,
    business: BusinessDocument,
    invoices: list[InvoiceDocument],
) -> bool:
    """
    An unpaid bill for minutes above the package makes the subscription
    past due; grace runs from the day the bill was issued (the owners
    were told the deadline then). False without such a bill.
    """

    unpaid_overage: list[InvoiceDocument] = [
        invoice
        for invoice in list_open_invoices(invoices)
        if invoice.kind is InvoiceKind.USAGE_OVERAGE
    ]
    if unpaid_overage == []:
        return False

    plan: PlanDefinition = plan_registry.get(subscription.plan_key)
    subscription.status = SubscriptionStatus.PAST_DUE
    subscription.grace_until = add_local_days(
        min(invoice.created_at for invoice in unpaid_overage),
        int(plan.grace_period_days),
        business.timezone,
    )
    return True
