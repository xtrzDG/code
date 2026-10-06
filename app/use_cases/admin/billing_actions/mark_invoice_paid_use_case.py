from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.referrals import ReferralEarningsFacilitatorContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import InvoiceStatus, SubscriptionStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.billing import (
    InvoiceDocument,
    ManualPayment,
    SubscriptionDocument,
)
from app.schemas.dto.admin_actions import AdminActionReceipt, MarkInvoicePaidCommand
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.use_cases.admin.billing_actions.account_action_gate import (
    INVOICE_ENTITY,
    AccountActionGate,
    AccountActionTarget,
    AdminActionRecord,
)
from app.use_cases.shared.billing_records import OPEN_INVOICE_STATUSES
from app.use_cases.shared.invoice_payments import record_invoice_payment
from app.use_cases.shared.service_mode_restoration import restore_full_service
from app.use_cases.shared.subscription_payment_transitions import (
    activate_paid_period,
)
from app.utilities.analytics.billing_event_drafts import subscription_started_events


class MarkInvoicePaidUseCase(
    UseCaseContract[MarkInvoicePaidCommand, AdminActionReceipt]
):
    """
    POST /v1/admin/clients/{business_id}/invoices/{invoice_id}/manual-payment:
    money for an open invoice came by bank transfer or in cash. The invoice
    is paid now, naming the method and the reference (its receipt says so),
    and a paid service period that has started becomes the subscription's
    current one, ends the grace and brings full service back, as a card
    payment would, and earns a referral what a card payment would. The audit
    log keeps the admin's reason (ADMIN_INVOICE_MARKED_PAID).

    Raises:
        NotFoundError: the client has no such invoice.
        ConflictError: the invoice is paid or voided already.
    """

    def __init__(
        self,
        gate: AccountActionGate,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        business_repo: BusinessRepoContract,
        product_events: RecordProductEventFacilitatorContract,
        wall_clock: WallClock[Microseconds],
        referral_earnings: ReferralEarningsFacilitatorContract,
    ) -> None:
        self._referral_earnings: ReferralEarningsFacilitatorContract = referral_earnings
        self._gate: AccountActionGate = gate
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._product_events: RecordProductEventFacilitatorContract = product_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: MarkInvoicePaidCommand) -> AdminActionReceipt:
        target: AccountActionTarget = self._gate.admit(
            input_data.user_id, input_data.business_id
        )
        invoice: InvoiceDocument | None = self._invoice_repo.get(
            target.business.id, input_data.invoice_id
        )
        if invoice is None:
            raise NotFoundError(f"Invoice {input_data.invoice_id} was not found.")

        if invoice.status not in OPEN_INVOICE_STATUSES:
            raise ConflictError("Only an open invoice can be marked paid.")

        now: Microseconds = self._wall_clock.now_unix()
        subscription: SubscriptionDocument = target.subscription
        previous_status: SubscriptionStatus = subscription.status
        with self._gate.transaction():
            record_invoice_payment(invoice, InvoiceStatus.PAID, None, now)
            invoice.manual_payment = ManualPayment(
                method=input_data.body.method,
                reference=input_data.body.reference,
                recorded_by=target.admin.id,
                recorded_at=now,
            )
            invoice.updated_at = now
            self._invoice_repo.save(invoice)
            if invoice.subscription_id == subscription.id:
                activate_paid_period(self._invoice_repo, subscription, now)
                subscription.updated_at = now
                self._subscription_repo.save(subscription)
                if subscription.status in {
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIALING,
                }:
                    restore_full_service(self._business_repo, target.business, now)

            receipt: AdminActionReceipt = self._gate.record(
                target,
                AdminActionRecord(
                    action=AuditAction.ADMIN_INVOICE_MARKED_PAID,
                    entity=INVOICE_ENTITY,
                    entity_id=str(invoice.id),
                    reason=input_data.body.reason,
                    client_ip_address=input_data.client_ip_address,
                ),
                now,
            )

        self._referral_earnings.record_paid_invoices(target.business, [invoice])
        self._product_events.record(
            *subscription_started_events(previous_status, subscription)
        )
        return receipt
