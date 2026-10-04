"""
After a payment, each invoice it paid is e-mailed with its receipt to the
billing e-mail (the owners' e-mail addresses without one), once.
"""

from app.orchestrators.billing.payment_webhook_orchestrator import (
    PaymentWebhookOrchestrator,
)
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.invoicing import BillingDocumentKind
from app.schemas.constants.payments import PaymentWebhookOutcome
from app.schemas.dto.invoicing import BillingEmailsQueued
from app.schemas.dto.payments import PaymentWebhookDelivery, PaymentWebhookReceipt
from app.schemas.typings.billing.strings import PaymentWebhookBody
from app.schemas.typings.invoicing.constrained_integers import BillingEmailCount
from app.transformers.invoicing.billing_document_email_transformer import (
    BillingDocumentEmailTransformer,
)
from app.use_cases.billing.send_payment_documents_use_case import (
    SendPaymentDocumentsUseCase,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.billing.paid_world import PaidWorld, checkout, payment_order
from tests.invoicing.attachment_fakes import RecordingStaffNotifier
from tests.invoicing.invoicing_world import build_seller_trial, save_billing_profile


def sender_of(
    world: PaidWorld, notifier: RecordingStaffNotifier
) -> SendPaymentDocumentsUseCase:
    testbed = world.testbed
    return SendPaymentDocumentsUseCase(
        payment_order_repo=testbed.payment_order_repo,
        business_repo=testbed.business_repo,
        invoice_repo=testbed.invoice_repo,
        billing_profile_repo=testbed.invoicing.billing_profile_repo,
        user_repo=testbed.user_repo,
        manager_notifier=notifier,
        email_transformer=BillingDocumentEmailTransformer(LocalizedTextResolver()),
    )


def paid_receipt(world: PaidWorld) -> PaymentWebhookReceipt:
    session = checkout(world)
    return world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(
            payment_order(world, session), "approved", masked_card="444455XXXXXX1111"
        )
    )


def test_the_paid_invoice_and_its_receipt_go_to_the_billing_email() -> None:
    world = build_seller_trial(is_vat_registered=True)
    save_billing_profile(world, "GE", billing_email="accounts@mtsvane-ezo.ge")
    receipt = paid_receipt(world)
    notifier = RecordingStaffNotifier()

    queued = sender_of(world, notifier).run(receipt)

    assert int(queued.queued) == 1
    [notification] = notifier.notifications
    invoice = world.testbed.invoices(world.business.id)[0]
    assert notification.contact.channel is ManagerContactChannel.EMAIL
    assert str(notification.contact.address) == "accounts@mtsvane-ezo.ge"
    assert str(notification.subject) == f"billing_documents:{invoice.id}"
    assert notification.billing_documents is not None
    assert notification.billing_documents.invoice_id == invoice.id
    assert notification.billing_documents.kinds == [
        BillingDocumentKind.INVOICE,
        BillingDocumentKind.RECEIPT,
    ]
    assert str(notification.billing_documents.language) == "ka"
    lines = str(notification.text).split("\n")
    assert lines[0] == "გადახდის ქვითარი, ინვოისი № AW-2026-000001"
    assert lines[1].startswith("Mtsvane Ezo: 610,06")
    assert "PDF" in lines[1]


def test_without_a_billing_email_the_owners_get_it() -> None:
    world = build_seller_trial(is_vat_registered=False)
    receipt = paid_receipt(world)
    notifier = RecordingStaffNotifier()

    sender_of(world, notifier).run(receipt)

    assert [str(item.contact.address) for item in notifier.notifications] == [
        "owner@example.com"
    ]


def test_owners_who_sign_in_by_phone_download_the_documents_instead() -> None:
    world = build_seller_trial(is_vat_registered=False)
    owner = world.testbed.user_repo.get(world.owner.id)
    assert owner is not None
    owner.email = None
    world.testbed.user_repo.save(owner)
    receipt = paid_receipt(world)
    notifier = RecordingStaffNotifier()

    queued = sender_of(world, notifier).run(receipt)

    assert int(queued.queued) == 0
    assert notifier.notifications == []


def test_nothing_is_sent_for_a_payment_that_paid_nothing() -> None:
    world = build_seller_trial(is_vat_registered=False)
    checkout(world)
    notifier = RecordingStaffNotifier()
    sender = sender_of(world, notifier)

    no_order = sender.run(PaymentWebhookReceipt(outcome=PaymentWebhookOutcome.APPLIED))

    assert int(no_order.queued) == 0
    assert notifier.notifications == []


class ScriptedWebhook:
    def __init__(self, outcome: PaymentWebhookOutcome) -> None:
        self.outcome: PaymentWebhookOutcome = outcome

    def run(self, input_data: PaymentWebhookDelivery) -> PaymentWebhookReceipt:
        del input_data
        return PaymentWebhookReceipt(outcome=self.outcome)


class RecordingSender:
    def __init__(self, error: Exception | None = None) -> None:
        self.receipts: list[PaymentWebhookReceipt] = []
        self.error: Exception | None = error

    def run(self, input_data: PaymentWebhookReceipt) -> BillingEmailsQueued:
        self.receipts.append(input_data)
        if self.error is not None:
            raise self.error

        return BillingEmailsQueued(queued=BillingEmailCount(0))


def test_the_webhook_mails_documents_only_after_a_payment_was_applied() -> None:
    delivery = PaymentWebhookDelivery(body=PaymentWebhookBody("{}"))
    for outcome, expected_calls in (
        (PaymentWebhookOutcome.APPLIED, 1),
        (PaymentWebhookOutcome.REFUND_DUE, 1),
        (PaymentWebhookOutcome.DUPLICATE, 0),
        (PaymentWebhookOutcome.IGNORED, 0),
    ):
        sender = RecordingSender()
        orchestrator = PaymentWebhookOrchestrator(ScriptedWebhook(outcome), sender)

        assert orchestrator.execute(delivery).outcome is outcome
        assert len(sender.receipts) == expected_calls


def test_a_failure_to_queue_the_e_mails_never_fails_the_webhook() -> None:
    sender = RecordingSender(error=RuntimeError("outbox down"))
    orchestrator = PaymentWebhookOrchestrator(
        ScriptedWebhook(PaymentWebhookOutcome.APPLIED), sender
    )

    receipt = orchestrator.execute(
        PaymentWebhookDelivery(body=PaymentWebhookBody("{}"))
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
