"""
Keys of the invoicing documents: the derived id of a business's billing
details, the key of a yearly invoice counter and the invoice number.
"""

from uuid import UUID, uuid5

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.invoicing.constrained_integers import (
    InvoiceSequenceNumber,
    InvoiceYear,
)
from app.schemas.typings.invoicing.constrained_strings import (
    InvoiceCounterKey,
    InvoiceNumber,
    InvoiceSeries,
)
from app.schemas.typings.invoicing.prefixed_id import BillingProfileId

# Fixed namespace of the derived ids (never change it: stored ids depend on it).
BILLING_PROFILE_NAMESPACE: UUID = UUID("3f6b2d8e-1c4a-4e7b-9a50-6d2c8f1e7b34")
NUMBER_DIGITS: int = 6


def derive_billing_profile_id(business_id: BusinessId) -> BillingProfileId:
    return BillingProfileId(uuid5(BILLING_PROFILE_NAMESPACE, str(business_id)))


def build_counter_key(series: InvoiceSeries, year: InvoiceYear) -> InvoiceCounterKey:
    """("AW", 2026) -> "AW:2026"."""

    return InvoiceCounterKey(f"{series}:{int(year)}")


def build_invoice_number(
    series: InvoiceSeries,
    year: InvoiceYear,
    sequence: InvoiceSequenceNumber,
) -> InvoiceNumber:
    """("AW", 2026, 42) -> "AW-2026-000042" (more digits past 999 999)."""

    return InvoiceNumber(f"{series}-{int(year)}-{int(sequence):0{NUMBER_DIGITS}d}")
