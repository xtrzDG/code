"""The invoicing parts of the billing testbed: billing details, numbers, VAT."""

from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.invoicing.invoice_issuing_facilitator import (
    InvoiceIssuingFacilitator,
)
from app.registries.billing.tax_policy_registry import TaxPolicyRegistry
from app.repositories.invoicing_repositories import (
    BillingProfileRepository,
    InvoiceCounterRepository,
)
from app.schemas.configurations.seller_settings import SellerSettings
from app.schemas.domain.billing_profiles import (
    BillingProfileDocument,
    InvoiceCounterDocument,
)


@dataclass(frozen=True)
class InvoicingParts:
    """In-memory billing details and counters, the tax policy and the issuer."""

    billing_profile_repo: BillingProfileRepository
    invoice_counter_repo: InvoiceCounterRepository
    tax_policy_registry: TaxPolicyRegistry
    invoice_issuing: InvoiceIssuingFacilitator


def build_invoicing_parts(
    seller: SellerSettings, wall_clock: WallClock[Microseconds]
) -> InvoicingParts:
    billing_profile_repo = BillingProfileRepository(
        InMemoryDocumentCollectionAdapter[BillingProfileDocument](
            BillingProfileDocument
        )
    )
    invoice_counter_repo = InvoiceCounterRepository(
        InMemoryDocumentCollectionAdapter[InvoiceCounterDocument](
            InvoiceCounterDocument
        )
    )
    tax_policy_registry = TaxPolicyRegistry(seller)
    return InvoicingParts(
        billing_profile_repo=billing_profile_repo,
        invoice_counter_repo=invoice_counter_repo,
        tax_policy_registry=tax_policy_registry,
        invoice_issuing=InvoiceIssuingFacilitator(
            billing_profile_repo=billing_profile_repo,
            invoice_counter_repo=invoice_counter_repo,
            tax_policy_registry=tax_policy_registry,
            seller=seller,
            wall_clock=wall_clock,
        ),
    )
