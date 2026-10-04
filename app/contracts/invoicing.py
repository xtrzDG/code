"""Invoicing seams: billing details, invoice numbers, VAT and the PDFs."""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.adapter_contract import AdapterContract
from app.contracts.facilitator_contract import FacilitatorContract
from app.contracts.registry_contract import RegistryContract
from app.contracts.repo_contract import RepoContract
from app.schemas.constants.invoicing import BillingDocumentKind
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.billing_profiles import BillingProfileDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.outbound_messages import OutboundBillingDocuments
from app.schemas.dto.billing import Money
from app.schemas.dto.invoicing import (
    BillingDocumentFile,
    TaxBuyer,
    TaxDecision,
    TaxedAmount,
)
from app.schemas.dto.messaging import EmailAttachment
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.invoicing.constrained_integers import (
    InvoiceSequenceNumber,
    InvoiceYear,
)
from app.schemas.typings.invoicing.constrained_strings import InvoiceSeries
from app.schemas.typings.invoicing.strings import BillingDocumentHtml
from app.schemas.typings.localization.constrained_strings import LanguageTag


class BillingProfileRepoContract(RepoContract, Protocol):
    def get_by_business(self, business_id: BusinessId) -> BillingProfileDocument | None:
        """The business's billing details, if the owner saved any."""
        raise NotImplementedError

    def save(self, profile: BillingProfileDocument) -> None:
        raise NotImplementedError


class InvoiceCounterRepoContract(RepoContract, Protocol):
    def take_next(
        self, series: InvoiceSeries, year: InvoiceYear, now: Microseconds
    ) -> InvoiceSequenceNumber:
        """
        The next number of a series in a year (1 for the first), taken by
        compare-and-set: concurrent callers, in any process, each get
        another number, and no number is ever given twice.

        Raises:
            ConflictError: other writers won every attempt (very busy).
        """
        raise NotImplementedError


class TaxPolicyRegistryContract(RegistryContract, Protocol):
    def decide(self, buyer: TaxBuyer) -> TaxDecision:
        """How VAT applies to this buyer's invoices from the seller."""
        raise NotImplementedError


class InvoiceDocumentRendererContract(AdapterContract, Protocol):
    def render(self, html: BillingDocumentHtml) -> bytes:
        """
        The PDF of a laid-out invoice or receipt. Nothing outside the HTML
        is fetched (no network, no files); fonts come from the system.

        Raises:
            ExternalServiceError: the PDF engine failed.
        """
        raise NotImplementedError


class InvoiceIssuingFacilitatorContract(FacilitatorContract, Protocol):
    def price_with_tax(self, business: BusinessDocument, net: Money) -> TaxedAmount:
        """A price before tax with the business's VAT on top."""
        raise NotImplementedError

    def issue(
        self, business: BusinessDocument, invoice: InvoiceDocument
    ) -> InvoiceDocument:
        """
        A new invoice whose `amount_minor` is the price before tax, made
        into the accountant's invoice: numbered, the seller and the buyer
        copied, the VAT added (`amount_minor` becomes the total). Not saved.
        """
        raise NotImplementedError

    def complete(
        self, business: BusinessDocument, invoice: InvoiceDocument
    ) -> InvoiceDocument:
        """
        An invoice issued before numbering (version 1) with a number and
        its parties, its amount left as it was charged (no VAT); one that
        has a number comes back as it is. Not saved.
        """
        raise NotImplementedError


class BillingDocumentFacilitatorContract(FacilitatorContract, Protocol):
    def produce(
        self,
        business: BusinessDocument,
        invoice: InvoiceDocument,
        kind: BillingDocumentKind,
        language: LanguageTag,
    ) -> BillingDocumentFile:
        """
        The PDF of a numbered invoice as an invoice or, once paid, a
        receipt, in `language` (English when the documents have no
        texts in it).

        Raises:
            ConflictError: a receipt of an unpaid invoice, or an invoice
                without a number.
            ExternalServiceError: the PDF could not be made.
        """
        raise NotImplementedError


class BillingEmailAttachmentsFacilitatorContract(FacilitatorContract, Protocol):
    def attach(
        self, business_id: BusinessId, documents: OutboundBillingDocuments
    ) -> list[EmailAttachment]:
        """
        The PDFs an e-mail to the billing contact carries, made now from
        the invoice as it is stored.

        Raises:
            NotFoundError: the business or the invoice no longer exists.
            ConflictError: a receipt of an invoice that is not paid.
            ExternalServiceError: the PDF could not be made (try again).
        """
        raise NotImplementedError
