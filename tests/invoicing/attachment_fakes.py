"""Fake makers of the invoice PDFs an outbox e-mail carries."""

from app.contracts.invoicing import BillingEmailAttachmentsFacilitatorContract
from app.schemas.domain.outbound_messages import OutboundBillingDocuments
from app.schemas.dto.messaging import EmailAttachment
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.messaging.constrained_strings import (
    EmailAttachmentFileName,
    EmailAttachmentMediaType,
)


class StaticBillingAttachments(BillingEmailAttachmentsFacilitatorContract):
    """One small PDF-shaped file per requested document; records requests."""

    def __init__(self) -> None:
        self.requests: list[tuple[BusinessId, OutboundBillingDocuments]] = []

    def attach(
        self, business_id: BusinessId, documents: OutboundBillingDocuments
    ) -> list[EmailAttachment]:
        self.requests.append((business_id, documents))
        return [
            EmailAttachment(
                file_name=EmailAttachmentFileName(f"{kind.value}.pdf"),
                media_type=EmailAttachmentMediaType("application/pdf"),
                content=b"%PDF-1.7 test",
            )
            for kind in documents.kinds
        ]
