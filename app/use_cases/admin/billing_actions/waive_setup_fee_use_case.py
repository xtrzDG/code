from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import InvoiceKind, InvoiceStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.dto.admin_actions import AdminActionReceipt, WaiveSetupFeeCommand
from app.schemas.exceptions.application_errors import ConflictError
from app.use_cases.admin.billing_actions.account_action_gate import (
    SUBSCRIPTION_ENTITY,
    AccountActionGate,
    AccountActionTarget,
    AdminActionRecord,
)
from app.use_cases.shared.billing_records import (
    OPEN_INVOICE_STATUSES,
    list_subscription_invoices,
)


class WaiveSetupFeeUseCase(UseCaseContract[WaiveSetupFeeCommand, AdminActionReceipt]):
    """
    POST /v1/admin/clients/{business_id}/setup-fee-waiver: the client no
    longer pays the done-for-you setup fee. Its unpaid setup fee bill is
    voided, and no setup fee is invoiced from now on. The audit log keeps
    the admin's reason (ADMIN_SETUP_FEE_WAIVED).

    Raises:
        ConflictError: the fee is waived already, or was paid (a refund is
            a matter for the payment provider).
    """

    def __init__(
        self,
        gate: AccountActionGate,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._gate: AccountActionGate = gate
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WaiveSetupFeeCommand) -> AdminActionReceipt:
        target: AccountActionTarget = self._gate.admit(
            input_data.user_id, input_data.business_id
        )
        subscription: SubscriptionDocument = target.subscription
        if subscription.is_setup_fee_waived:
            raise ConflictError("The setup fee is waived already.")

        setup_fees: list[InvoiceDocument] = [
            invoice
            for invoice in list_subscription_invoices(self._invoice_repo, subscription)
            if invoice.kind is InvoiceKind.SETUP_FEE
        ]
        if any(invoice.status is InvoiceStatus.PAID for invoice in setup_fees):
            raise ConflictError("The setup fee is paid already.")

        now: Microseconds = self._wall_clock.now_unix()
        with self._gate.transaction():
            for invoice in setup_fees:
                if invoice.status in OPEN_INVOICE_STATUSES:
                    invoice.status = InvoiceStatus.VOID
                    invoice.updated_at = now
                    self._invoice_repo.save(invoice)

            subscription.is_setup_fee_waived = True
            subscription.updated_at = now
            self._subscription_repo.save(subscription)
            return self._gate.record(
                target,
                AdminActionRecord(
                    action=AuditAction.ADMIN_SETUP_FEE_WAIVED,
                    entity=SUBSCRIPTION_ENTITY,
                    entity_id=str(subscription.id),
                    reason=input_data.body.reason,
                    client_ip_address=input_data.client_ip_address,
                ),
                now,
            )
