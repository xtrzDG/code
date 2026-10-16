"""
An outbox e-mail to the billing contact carries the invoice PDFs, made
when it is sent: queued with the documents it names, attached by the
staff sender, written by SMTP as attachments.
"""

from app.facilitators.invoicing.billing_email_attachments_facilitator import (
    BillingEmailAttachmentsFacilitator,
)
from app.facilitators.notifications.staff_notification_sender_facilitator import (
    StaffNotificationSenderFacilitator,
)
from app.schemas.constants.deliveries import DeliveryFailureKind
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.invoicing import BillingDocumentKind
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.outbound_messages import OutboundBillingDocuments
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.messaging import EmailAttachment
from app.schemas.typings.billing.prefixed_id import InvoiceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.messaging.constrained_strings import (
    EmailAttachmentFileName,
    EmailAttachmentMediaType,
)
from app.schemas.typings.messaging.strings import EmailBodyText, EmailSubject
from app.schemas.typings.notifications.constrained_strings import StaffAlertSubject
from app.use_cases.channels.outbox.send_outbound_message_use_case import (
    SendOutboundMessageUseCase,
)
from app.utilities.deliveries.delivery_keys import (
    derive_outbound_message_id,
    staff_idempotency_key,
)
from tests.billing.paid_world import checkout
from tests.channels.channels_inbox import ChannelsInbox
from tests.invoicing.attachment_fakes import CapturingMailer, StaticBillingAttachments
from tests.invoicing.document_world import HtmlEchoRenderer, build_document_world
from tests.invoicing.invoicing_world import build_seller_trial
from tests.users.test_smtp_email_client import (
    RECIPIENT,
    Connections,
    FakeSmtp,
    build_client,
)

DOCUMENTS = OutboundBillingDocuments(
    invoice_id=InvoiceId(),
    kinds=[BillingDocumentKind.INVOICE, BillingDocumentKind.RECEIPT],
    language=LanguageTag("ru"),
)


def contact(channel: ManagerContactChannel, address: str) -> ManagerContact:
    return ManagerContact(
        name=ManagerName("Accounts"),
        channel=channel,
        address=ManagerContactAddress(address),
        language=LanguageTag("ru"),
    )


def send_one(
    channel: ManagerContactChannel, address: str
) -> tuple[CapturingMailer, StaticBillingAttachments, DeliveryFailureKind | None]:
    inbox = ChannelsInbox()
    mailer = CapturingMailer()
    attachments = StaticBillingAttachments()
    business_id = BusinessId()
    recipient = contact(channel, address)
    subject = StaffAlertSubject(f"billing_documents:{DOCUMENTS.invoice_id}")
    assert inbox.staff_notifier.notify(
        StaffNotification(
            business_id=business_id,
            contact=recipient,
            text=MessageText("Квитанция об оплате по счёту № AW-2026-000001\nСпасибо"),
            subject=subject,
            billing_documents=DOCUMENTS,
        )
    )
    queued = inbox.outbound_message_repo.get(
        business_id,
        derive_outbound_message_id(
            business_id, staff_idempotency_key(recipient, None, subject)
        ),
    )
    assert queued is not None
    assert queued.billing_documents == DOCUMENTS
    send = SendOutboundMessageUseCase(
        inbox.telegram_adapter,
        inbox.whatsapp_adapter,
        inbox.messenger_adapter,
        inbox.instagram_adapter,
        inbox.channel_repo,
        inbox.secret_cipher,
        StaffNotificationSenderFacilitator(
            inbox.telegram_client,
            inbox.whatsapp_adapter,
            inbox.settings,
            email_client=mailer,
        ),
        inbox.push_sender,
        inbox.usage_event_repo,
        inbox.wall_clock,
        inbox.whatsapp_adapter,
        attachments,
    )
    return mailer, attachments, send.run(queued).failure


def test_the_outbox_attaches_the_invoice_pdfs_made_at_sending() -> None:
    mailer, attachments, failure = send_one(
        ManagerContactChannel.EMAIL, "accounts@mtsvane-ezo.ge"
    )

    assert failure is None
    assert len(attachments.requests) == 1
    [(recipient, subject, files)] = mailer.sent
    assert str(recipient) == "accounts@mtsvane-ezo.ge"
    assert str(subject) == "Квитанция об оплате по счёту № AW-2026-000001"
    assert [str(file.file_name) for file in files] == ["invoice.pdf", "receipt.pdf"]


def test_only_e_mail_carries_files() -> None:
    mailer, _, failure = send_one(ManagerContactChannel.SMS, "+995599123456")

    assert failure is DeliveryFailureKind.REJECTED
    assert mailer.sent == []


def test_smtp_writes_the_pdfs_as_attachments() -> None:
    connections = Connections(FakeSmtp())
    pdf = EmailAttachment(
        file_name=EmailAttachmentFileName("receipt-AW-2026-000001.pdf"),
        media_type=EmailAttachmentMediaType("application/pdf"),
        content=b"%PDF-1.7 receipt",
    )

    build_client(connections).send_email(
        recipient=RECIPIENT,
        subject=EmailSubject("Квитанция"),
        text_body=EmailBodyText("Спасибо"),
        html_body=EmailBodyText("<p>Спасибо</p>"),
        attachments=[pdf],
    )

    [message] = connections.smtp.sent
    [attached] = list(message.iter_attachments())
    assert attached.get_content_type() == "application/pdf"
    assert attached.get_filename() == "receipt-AW-2026-000001.pdf"
    assert attached.get_content() == b"%PDF-1.7 receipt"


def test_the_attachments_are_the_invoice_documents_of_the_stored_invoice() -> None:
    world = build_seller_trial(is_vat_registered=False)
    checkout(world)
    testbed = world.testbed
    invoice = testbed.invoices(world.business.id)[0]
    documents = build_document_world(world, HtmlEchoRenderer()).documents
    facilitator = BillingEmailAttachmentsFacilitator(
        testbed.business_repo, testbed.invoice_repo, documents
    )

    files = facilitator.attach(
        world.business.id,
        OutboundBillingDocuments(
            invoice_id=invoice.id,
            kinds=[BillingDocumentKind.INVOICE],
            language=LanguageTag("en"),
        ),
    )

    [file] = files
    assert str(file.file_name) == "invoice-AW-2026-000001.pdf"
    assert str(file.media_type) == "application/pdf"
    assert b"<h1>Invoice</h1>" in file.content
