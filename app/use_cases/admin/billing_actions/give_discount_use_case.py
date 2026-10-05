from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.billing import SubscriptionDiscount, SubscriptionDocument
from app.schemas.dto.admin_actions import AdminActionReceipt, GiveDiscountCommand
from app.use_cases.admin.billing_actions.account_action_gate import (
    SUBSCRIPTION_ENTITY,
    AccountActionGate,
    AccountActionTarget,
    AdminActionRecord,
)
from app.utilities.billing.discount_days import discount_ends_at


class GiveDiscountUseCase(UseCaseContract[GiveDiscountCommand, AdminActionReceipt]):
    """
    POST /v1/admin/clients/{business_id}/discount: to close a deal, the
    client pays `percent` less for every service period that starts on or
    before `last_day` (in its time zone). The discount comes off the price
    before tax when the period's bill is issued (`IssueDueInvoicesUseCase`);
    a period the payment provider charges on its own schedule keeps the
    amount agreed at checkout. A new discount replaces the earlier one. The
    audit log keeps the admin's reason (ADMIN_DISCOUNT_GIVEN).

    Raises:
        ValidationFailedError: the last day is not a calendar day, is over,
            or is more than three years ahead.
    """

    def __init__(
        self,
        gate: AccountActionGate,
        subscription_repo: SubscriptionRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._gate: AccountActionGate = gate
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: GiveDiscountCommand) -> AdminActionReceipt:
        target: AccountActionTarget = self._gate.admit(
            input_data.user_id, input_data.business_id
        )
        subscription: SubscriptionDocument = target.subscription
        now: Microseconds = self._wall_clock.now_unix()
        ends_at: Microseconds = discount_ends_at(
            input_data.body.last_day, target.business.timezone, now
        )
        with self._gate.transaction():
            subscription.discount = SubscriptionDiscount(
                percent=input_data.body.percent,
                ends_at=ends_at,
                granted_by=target.admin.id,
                granted_at=now,
            )
            subscription.updated_at = now
            self._subscription_repo.save(subscription)
            return self._gate.record(
                target,
                AdminActionRecord(
                    action=AuditAction.ADMIN_DISCOUNT_GIVEN,
                    entity=SUBSCRIPTION_ENTITY,
                    entity_id=str(subscription.id),
                    reason=input_data.body.reason,
                    client_ip_address=input_data.client_ip_address,
                ),
                now,
            )
