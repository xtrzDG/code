"""
Records of business B for the billing document operations of the matrix:
an invoice (the demo restaurant is in its trial and has none yet) and the
document to print, and the body of the billing details.
"""

from typing import Any

from typed_time_provider import Microseconds

from app.schemas.constants.billing import InvoiceKind, InvoiceStatus
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from tests.e2e.harness import Workshop

B: str = "/v1/businesses/{business_id}"

BILLING_BODIES: dict[str, dict[str, object]] = {
    f"PUT {B}/billing/profile": {"legal_name": "Mtsvane Ezo LLC", "country_code": "GE"},
}
# 2026-10-01 00:00 UTC to 2026-11-01 00:00 UTC.
PERIOD_START: Microseconds = Microseconds(1_790_812_800_000_000)
PERIOD_END: Microseconds = Microseconds(1_793_491_200_000_000)


def billing_path_values(
    workshop: Workshop,
    storage_scope: Any,
    business_id: str,
) -> dict[str, str]:
    """invoice_id: an issued invoice of business B; document_kind: its PDF."""

    business_key = BusinessId(business_id)
    invoice = InvoiceDocument(
        business_id=business_key,
        kind=InvoiceKind.SERVICE_PERIOD,
        description=InvoiceDescription("Call and message handling service"),
        amount_minor=MoneyAmountMinor(51_700),
        currency_code=CurrencyCode("GEL"),
        status=InvoiceStatus.ISSUED,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        created_at=PERIOD_START,
        updated_at=PERIOD_START,
    )
    with storage_scope.scoped_to_business(business_key):
        workshop.container.repositories.invoice_repo().save(invoice)

    return {"invoice_id": str(invoice.id), "document_kind": "invoice"}
