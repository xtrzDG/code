"""Fakes of the invoice e-mails: the PDFs, the mailer and the notifier."""

from collections.abc import Sequence

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.invoicing import BillingEmailAttachmentsFacilitatorContract
from app.contracts.messaging_clients import EmailSenderClientContract
from app.schemas.domain.outbound_messages import OutboundBillingDocuments
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.messaging import EmailAttachment
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.messaging.constrained_strings import (
    EmailAttachmentFileName,
    EmailAttachmentMediaType,
)
from app.schemas.typings.messaging.strings import EmailBodyText, EmailSubject
from app.schemas.typings.users.constrained_strings import EmailAddress


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


class CapturingMailer(EmailSenderClientContract):
    """Keeps every e-mail with the files attached to it."""

    def __init__(self) -> None:
        self.sent: list[tuple[EmailAddress, EmailSubject, list[EmailAttachment]]] = []

    def send_email(
        self,
        recipient: EmailAddress,
        subject: EmailSubject,
        text_body: EmailBodyText,
        html_body: EmailBodyText | None,
        attachments: Sequence[EmailAttachment] = (),
    ) -> None:
        del text_body, html_body
        self.sent.append((recipient, subject, list(attachments)))


class RecordingStaffNotifier(ManagerNotificationFacilitatorContract):
    """Keeps every staff notification as it was asked for."""

    def __init__(self) -> None:
        self.notifications: list[StaffNotification] = []

    def notify(self, notification: StaffNotification) -> bool:
        self.notifications.append(notification)
        return True
