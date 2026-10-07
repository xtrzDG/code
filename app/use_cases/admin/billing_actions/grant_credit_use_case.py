from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.client_care_repositories import (
    BillingCreditRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import BillingCreditKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.billing_credits import BillingCreditDocument
from app.schemas.dto.admin_actions import AdminActionReceipt, GrantCreditCommand
from app.use_cases.admin.billing_actions.account_action_gate import (
    BILLING_CREDIT_ENTITY,
    AccountActionGate,
    AccountActionTarget,
    AdminActionRecord,
)


class GrantCreditUseCase(UseCaseContract[GrantCreditCommand, AdminActionReceipt]):
    """
    POST /v1/admin/clients/{business_id}/credits: credit in the
    subscription's currency goes to the client's ledger (`billing_credits`)
    with who granted it and why. The next invoices the platform issues to
    be paid use it before tax, until it is spent; an invoice voided later
    gives its credit back. The audit log keeps the reason
    (ADMIN_CREDIT_GRANTED).
    """

    def __init__(
        self,
        gate: AccountActionGate,
        billing_credit_repo: BillingCreditRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._gate: AccountActionGate = gate
        self._billing_credit_repo: BillingCreditRepoContract = billing_credit_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: GrantCreditCommand) -> AdminActionReceipt:
        target: AccountActionTarget = self._gate.admit(
            input_data.user_id, input_data.business_id
        )
        now: Microseconds = self._wall_clock.now_unix()
        line = BillingCreditDocument(
            business_id=target.business.id,
            kind=BillingCreditKind.GRANTED,
            amount_minor=input_data.body.amount_minor,
            currency_code=target.subscription.currency_code,
            granted_by=target.admin.id,
            reason=input_data.body.reason,
            created_at=now,
            updated_at=now,
        )
        with self._gate.transaction():
            self._billing_credit_repo.record(line)
            return self._gate.record(
                target,
                AdminActionRecord(
                    action=AuditAction.ADMIN_CREDIT_GRANTED,
                    entity=BILLING_CREDIT_ENTITY,
                    entity_id=str(line.id),
                    reason=input_data.body.reason,
                    client_ip_address=input_data.client_ip_address,
                ),
                now,
            )
