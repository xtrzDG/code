from app.contracts.invoicing import (
    BillingDocumentFacilitatorContract,
    BillingEmailAttachmentsFacilitatorContract,
)
from app.contracts.repositories.billing_repositories import InvoiceRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.outbound_messages import OutboundBillingDocuments
from app.schemas.dto.invoicing import BillingDocumentFile
from app.schemas.dto.messaging import EmailAttachment
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.messaging.constrained_strings import (
    EmailAttachmentFileName,
    EmailAttachmentMediaType,
)

PDF_MEDIA_TYPE: EmailAttachmentMediaType = EmailAttachmentMediaType("application/pdf")


class BillingEmailAttachmentsFacilitator(BillingEmailAttachmentsFacilitatorContract):
    """
    The invoice and receipt PDFs of an outbox e-mail, made when it is sent
    (the outbox stores which documents, never their bytes), so a retry
    after a failure attaches the same documents again.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        invoice_repo: InvoiceRepoContract,
        billing_documents: BillingDocumentFacilitatorContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._billing_documents: BillingDocumentFacilitatorContract = billing_documents

    def attach(
        self, business_id: BusinessId, documents: OutboundBillingDocuments
    ) -> list[EmailAttachment]:
        business: BusinessDocument | None = self._business_repo.get(business_id)
        invoice: InvoiceDocument | None = self._invoice_repo.get(
            business_id, documents.invoice_id
        )
        if business is None or invoice is None:
            raise NotFoundError("The invoice of this e-mail no longer exists.")

        attachments: list[EmailAttachment] = []
        for kind in documents.kinds:
            document: BillingDocumentFile = self._billing_documents.produce(
                business, invoice, kind, documents.language
            )
            attachments.append(
                EmailAttachment(
                    file_name=EmailAttachmentFileName(str(document.file_name)),
                    media_type=PDF_MEDIA_TYPE,
                    content=document.content,
                )
            )

        return attachments
