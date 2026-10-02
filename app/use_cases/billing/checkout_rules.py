"""What a checkout collects: whether the service itself is unpaid, the order line."""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import InvoiceKind, SubscriptionStatus
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.typings.billing.strings import InvoiceDescription
from app.use_cases.billing.billing_records import find_covering_paid_invoice


def is_service_unpaid(
    subscription: SubscriptionDocument,
    invoices: list[InvoiceDocument],
    open_invoices: list[InvoiceDocument],
    now: Microseconds,
) -> bool:
    """
    Only other bills (e.g. minutes above the package) are open while the
    subscription is not active and no paid period or running trial
    covers now: the service itself must be paid too, or paying would
    not restore it. An active subscription is renewed by its automatic
    charges instead.
    """

    is_trial_running: bool = (
        subscription.trial_ends_at is not None and now < subscription.trial_ends_at
    )
    return (
        subscription.status is not SubscriptionStatus.ACTIVE
        and not is_trial_running
        and find_covering_paid_invoice(invoices, now) is None
        and all(
            invoice.kind is not InvoiceKind.SERVICE_PERIOD for invoice in open_invoices
        )
    )


def select_order_description(invoices: list[InvoiceDocument]) -> InvoiceDescription:
    """The service-period line when there is one, else the first invoice line."""

    for invoice in invoices:
        if invoice.kind is InvoiceKind.SERVICE_PERIOD:
            return invoice.description

    return invoices[0].description
