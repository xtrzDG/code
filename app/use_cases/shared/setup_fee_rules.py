"""When the one-time setup fee is still to be invoiced to a business."""

from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    SetupOption,
)
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument


def is_setup_fee_pending(
    subscription: SubscriptionDocument,
    business_invoices: list[InvoiceDocument],
) -> bool:
    """
    The setup fee is still to be invoiced: a monthly subscription the
    platform team sets up (DONE_FOR_YOU), the fee not waived, and the
    business never invoiced one (a void one aside) nor paid any service
    period (an annual payment includes the fee). Whether a brand's other
    location carries the fee is asked separately (`brand_billing.py`).
    """

    if (
        subscription.billing_period is not BillingPeriod.MONTHLY
        or subscription.setup_option is not SetupOption.DONE_FOR_YOU
        or subscription.is_setup_fee_waived
    ):
        return False

    return not any(
        (
            invoice.kind is InvoiceKind.SETUP_FEE
            and invoice.status is not InvoiceStatus.VOID
        )
        or (
            invoice.kind is InvoiceKind.SERVICE_PERIOD
            and invoice.status is InvoiceStatus.PAID
        )
        for invoice in business_invoices
    )
