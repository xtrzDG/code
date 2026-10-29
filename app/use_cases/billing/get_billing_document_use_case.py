from typed_time_provider import Microseconds, WallClock

from app.contracts.invoicing import (
    BillingDocumentFacilitatorContract,
    InvoiceIssuingFacilitatorContract,
)
from app.contracts.repositories.billing_repositories import InvoiceRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import InvoiceStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.invoicing import BillingDocumentFile, BillingDocumentQuery
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.babel_locales import require_babel_locale

BILLING_DOCUMENT_ENTITY: AuditEntityName = AuditEntityName("billing_document")


class GetBillingDocumentUseCase(
    UseCaseContract[BillingDocumentQuery, BillingDocumentFile]
):
    """
    An owner downloads the PDF of an invoice, or of its receipt once paid,
    in the requested language (the owner language by default). An invoice
    from before numbering gets its number and parties now (kept, so every
    later download prints the same), its amount as it was charged. The
    document names the buyer, so each download is audited as an export.

    Raises:
        NotFoundError: no such invoice in the business.
        ConflictError: a receipt of an unpaid invoice, or an invoice voided
            before it was ever numbered.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        invoice_repo: InvoiceRepoContract,
        invoice_issuing: InvoiceIssuingFacilitatorContract,
        billing_documents: BillingDocumentFacilitatorContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._invoice_issuing: InvoiceIssuingFacilitatorContract = invoice_issuing
        self._billing_documents: BillingDocumentFacilitatorContract = billing_documents
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: BillingDocumentQuery) -> BillingDocumentFile:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        language: LanguageTag = input_data.display_language or business.owner_language
        require_babel_locale(language)
        invoice: InvoiceDocument | None = self._invoice_repo.get(
            business.id, input_data.invoice_id
        )
        if invoice is None:
            raise NotFoundError("Invoice not found.")

        invoice = self._numbered(business, invoice)
        document: BillingDocumentFile = self._billing_documents.produce(
            business, invoice, input_data.kind, language
        )
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.EXPORT,
                entity=BILLING_DOCUMENT_ENTITY,
                entity_id=AuditEntityReference(str(document.file_name)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return document

    def _numbered(
        self, business: BusinessDocument, invoice: InvoiceDocument
    ) -> InvoiceDocument:
        if invoice.number is not None:
            return invoice

        if invoice.status is InvoiceStatus.VOID:
            raise ConflictError("This invoice was cancelled before it was numbered.")

        completed: InvoiceDocument = self._invoice_issuing.complete(business, invoice)
        completed.updated_at = self._wall_clock.now_unix()
        self._invoice_repo.save(completed)
        return completed
