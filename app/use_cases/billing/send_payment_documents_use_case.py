from app.contracts.billing import PaymentOrderRepoContract
from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.invoicing import BillingProfileRepoContract
from app.contracts.repositories.billing_repositories import InvoiceRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import InvoiceStatus
from app.schemas.constants.invoicing import BillingDocumentKind
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.billing_profiles import BillingProfileDocument
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.outbound_messages import OutboundBillingDocuments
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.invoicing import BillingDocumentEmailInput, BillingEmailsQueued
from app.schemas.dto.payments import PaymentWebhookReceipt
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.invoicing.constrained_integers import BillingEmailCount
from app.schemas.typings.notifications.constrained_strings import StaffAlertSubject
from app.use_cases.billing.billing_contacts import find_billing_contacts

NOTHING_QUEUED: BillingEmailsQueued = BillingEmailsQueued(queued=BillingEmailCount(0))
SENT_DOCUMENTS: list[BillingDocumentKind] = [
    BillingDocumentKind.INVOICE,
    BillingDocumentKind.RECEIPT,
]


class SendPaymentDocumentsUseCase(
    UseCaseContract[PaymentWebhookReceipt, BillingEmailsQueued]
):
    """
    After a payment notification, e-mail each invoice it paid, with the
    invoice and its receipt as PDFs, to the business's billing e-mail (the
    owners' e-mail addresses when no billing e-mail is saved). The e-mails
    go through the outbox, once per invoice and address, so a repeated
    notification queues nothing new; the PDFs are made when they are sent,
    in the owner language.
    """

    def __init__(
        self,
        payment_order_repo: PaymentOrderRepoContract,
        business_repo: BusinessRepoContract,
        invoice_repo: InvoiceRepoContract,
        billing_profile_repo: BillingProfileRepoContract,
        user_repo: UserRepoContract,
        manager_notifier: ManagerNotificationFacilitatorContract,
        email_transformer: TransformerContract[BillingDocumentEmailInput, MessageText],
    ) -> None:
        self._payment_order_repo: PaymentOrderRepoContract = payment_order_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._billing_profile_repo: BillingProfileRepoContract = billing_profile_repo
        self._user_repo: UserRepoContract = user_repo
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._email_transformer: TransformerContract[
            BillingDocumentEmailInput, MessageText
        ] = email_transformer

    def run(self, input_data: PaymentWebhookReceipt) -> BillingEmailsQueued:
        if input_data.payment_order_id is None:
            return NOTHING_QUEUED

        order: PaymentOrderDocument | None = self._payment_order_repo.get(
            input_data.payment_order_id
        )
        if order is None or order.last_payment_reference is None:
            return NOTHING_QUEUED

        business: BusinessDocument | None = self._business_repo.get(order.business_id)
        if business is None:
            return NOTHING_QUEUED

        paid: list[InvoiceDocument] = [
            invoice
            for invoice in self._invoice_repo.list_by_business(business.id)
            if invoice.status is InvoiceStatus.PAID
            and invoice.paid_at is not None
            and invoice.number is not None
            and invoice.provider_reference == order.last_payment_reference
        ]
        if paid == []:
            return NOTHING_QUEUED

        profile: BillingProfileDocument | None = (
            self._billing_profile_repo.get_by_business(business.id)
        )
        contacts: list[ManagerContact] = find_billing_contacts(
            business, profile, self._user_repo
        )
        queued: int = sum(
            self._queue(business, invoice, contact)
            for invoice in paid
            for contact in contacts
        )
        return BillingEmailsQueued(queued=BillingEmailCount(queued))

    def _queue(
        self,
        business: BusinessDocument,
        invoice: InvoiceDocument,
        contact: ManagerContact,
    ) -> int:
        text: MessageText = self._email_transformer.transform(
            BillingDocumentEmailInput(
                invoice=invoice,
                business_name=business.name,
                language=business.owner_language,
                timezone=business.timezone,
            )
        )
        is_queued: bool = self._manager_notifier.notify(
            StaffNotification(
                business_id=business.id,
                contact=contact,
                text=text,
                subject=StaffAlertSubject(f"billing_documents:{invoice.id}"),
                billing_documents=OutboundBillingDocuments(
                    invoice_id=invoice.id,
                    kinds=SENT_DOCUMENTS,
                    language=business.owner_language,
                ),
            )
        )
        return 1 if is_queued else 0
