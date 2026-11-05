from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.admin_actions import AdminActionReceipt, ExtendTrialCommand
from app.schemas.exceptions.application_errors import ConflictError
from app.use_cases.admin.billing_actions.account_action_gate import (
    SUBSCRIPTION_ENTITY,
    AccountActionGate,
    AccountActionTarget,
    AdminActionRecord,
)
from app.use_cases.shared.billing_records import list_subscription_invoices
from app.use_cases.shared.trial_subscriptions import void_unpaid_invoices
from app.utilities.billing.billing_periods import add_local_days


class ExtendTrialUseCase(UseCaseContract[ExtendTrialCommand, AdminActionReceipt]):
    """
    POST /v1/admin/clients/{business_id}/trial-extension: a slow onboarding
    gets more days of its free trial.

    A running trial ends `days` later. A trial that ended unpaid (past due,
    no service period ever paid) runs again for `days` from now: the bills
    of its first period are voided, the grace ends and the assistant is back
    to full service. The audit log keeps the admin's reason
    (ADMIN_TRIAL_EXTENDED).

    Raises:
        ConflictError: the client has no trial to extend (it pays already,
            or never had one).
    """

    def __init__(
        self,
        gate: AccountActionGate,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        business_repo: BusinessRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._gate: AccountActionGate = gate
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ExtendTrialCommand) -> AdminActionReceipt:
        target: AccountActionTarget = self._gate.admit(
            input_data.user_id, input_data.business_id
        )
        subscription: SubscriptionDocument = target.subscription
        now: Microseconds = self._wall_clock.now_unix()
        days: int = int(input_data.body.days)
        with self._gate.transaction():
            if self._is_trial(subscription):
                ends_at: Microseconds = subscription.trial_ends_at or now
                self._extend(target, max(ends_at, now, key=int), days)
            elif self._is_unpaid_ended_trial(subscription):
                void_unpaid_invoices(self._invoice_repo, subscription, now)
                subscription.status = SubscriptionStatus.TRIALING
                subscription.period_start = now
                subscription.grace_until = None
                self._extend(target, now, days)
                self._restore_full_service(target.business, now)
            else:
                raise ConflictError(
                    "Only a free trial, running or ended unpaid, can be extended."
                )

            subscription.updated_at = now
            self._subscription_repo.save(subscription)
            return self._gate.record(
                target,
                AdminActionRecord(
                    action=AuditAction.ADMIN_TRIAL_EXTENDED,
                    entity=SUBSCRIPTION_ENTITY,
                    entity_id=str(subscription.id),
                    reason=input_data.body.reason,
                    client_ip_address=input_data.client_ip_address,
                ),
                now,
            )

    def _is_trial(self, subscription: SubscriptionDocument) -> bool:
        """A trial, also one whose end the trial job has not handled yet."""

        return (
            subscription.status is SubscriptionStatus.TRIALING
            and subscription.trial_ends_at is not None
        )

    def _is_unpaid_ended_trial(self, subscription: SubscriptionDocument) -> bool:
        if (
            subscription.status is not SubscriptionStatus.PAST_DUE
            or subscription.trial_ends_at is None
        ):
            return False

        return not any(
            invoice.kind is InvoiceKind.SERVICE_PERIOD
            and invoice.status is InvoiceStatus.PAID
            for invoice in list_subscription_invoices(self._invoice_repo, subscription)
        )

    def _extend(
        self, target: AccountActionTarget, start: Microseconds, days: int
    ) -> None:
        subscription: SubscriptionDocument = target.subscription
        trial_ends_at: Microseconds = add_local_days(
            start, days, target.business.timezone
        )
        subscription.trial_ends_at = trial_ends_at
        subscription.period_end = trial_ends_at

    def _restore_full_service(
        self, business: BusinessDocument, now: Microseconds
    ) -> None:
        def switch_to_full_service(current: BusinessDocument) -> None:
            if current.service_mode is not ServiceMode.FULL:
                current.service_mode = ServiceMode.FULL
                current.updated_at = now

        self._business_repo.update(business.id, switch_to_full_service)
