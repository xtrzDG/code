from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
    BusinessDeletionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.business_closures import (
    BusinessClosureReason,
    ClosureNoticeKind,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.business_closures import BusinessClosureDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.business_closures.constrained_integers import (
    OffboardAfterDays,
)
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.businesses.closure.close_business_use_case import CLOSURE_ENTITY
from app.use_cases.businesses.closure.closure_cancellation import cancel_closure
from app.use_cases.businesses.closure.closure_effects import ClosureEffects
from app.use_cases.businesses.closure.closure_notices import ClosureNotices
from app.use_cases.businesses.closure.closure_rules import (
    deletion_moment,
    offboarding_moment,
)
from app.use_cases.businesses.closure.unpaid_ends import unpaid_end
from app.use_cases.shared.billing_records import (
    find_current_subscription,
    is_service_paid_for,
    list_subscription_invoices,
)
from app.use_cases.shared.business_walk import walk_businesses
from app.utilities.business_closures.closure_identity import closure_id_for


class OffboardUnpaidBusinessesUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Daily, across businesses (`offboard_unpaid_businesses`, DPA 13.3): a
    business whose subscription ended unpaid OFFBOARD_AFTER_DAYS ago (a
    missed payment past its grace, or a cancelled subscription past the
    last period paid for) is closed automatically: pending deletion for 30
    days like an owner's closure (the assistant paused, the channels off,
    the full export still offered), and every owner is told how to keep it.
    Paying again reopens it: the job cancels such a closure while its
    deletion has not begun. Businesses that never paid (still setting up)
    are left alone.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        closure_repo: BusinessClosureRepoContract,
        deletion_repo: BusinessDeletionRepoContract,
        effects: ClosureEffects,
        notices: ClosureNotices,
        audit_log_repo: AuditLogRepoContract,
        offboard_after: OffboardAfterDays,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._closure_repo: BusinessClosureRepoContract = closure_repo
        self._deletion_repo: BusinessDeletionRepoContract = deletion_repo
        self._effects: ClosureEffects = effects
        self._notices: ClosureNotices = notices
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._offboard_after: OffboardAfterDays = offboard_after
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        changed: int = 0
        for business in walk_businesses(self._business_repo):
            now: Microseconds = self._wall_clock.now_unix()
            subscription: SubscriptionDocument | None = find_current_subscription(
                self._subscription_repo, business.id
            )
            closure: BusinessClosureDocument | None = self._closure_repo.get(
                business.id
            )
            if closure is not None:
                changed += int(
                    self._reopen_if_paid(business, closure, subscription, now)
                )
            elif self._is_unpaid_long_enough(subscription, now):
                changed += int(self._close(business, now))

        return JobReport(processed_count=ProcessedItemCount(changed))

    def _is_unpaid_long_enough(
        self, subscription: SubscriptionDocument | None, now: Microseconds
    ) -> bool:
        if subscription is None:
            return False

        since: Microseconds | None = unpaid_end(
            subscription,
            list_subscription_invoices(self._invoice_repo, subscription),
            now,
        )
        return since is not None and now >= offboarding_moment(
            since, self._offboard_after
        )

    def _close(self, business: BusinessDocument, now: Microseconds) -> bool:
        if self._deletion_repo.find_by_business(business.id) is not None:
            return False

        closure = BusinessClosureDocument(
            id=closure_id_for(business.id),
            business_id=business.id,
            reason=BusinessClosureReason.UNPAID_SUBSCRIPTION,
            requested_at=now,
            delete_after=deletion_moment(now),
            status_before=business.status,
            created_at=now,
            updated_at=now,
        )
        if not self._closure_repo.open(closure):
            return False

        self._effects.pause(business.id, now)
        disconnected = self._effects.disconnect_channels(business.id, now)

        def remember(stored: BusinessClosureDocument) -> BusinessClosureDocument:
            stored.disconnected_channel_ids = disconnected
            return stored

        self._closure_repo.modify(business.id, remember)
        self._audit(business, AuditAction.CREATE, now)
        self._notices.send(business, closure, ClosureNoticeKind.OPENED_UNPAID, None)
        return True

    def _reopen_if_paid(
        self,
        business: BusinessDocument,
        closure: BusinessClosureDocument,
        subscription: SubscriptionDocument | None,
        now: Microseconds,
    ) -> bool:
        if (
            closure.reason is not BusinessClosureReason.UNPAID_SUBSCRIPTION
            or closure.deletion_queued_at is not None
            or not is_service_paid_for(subscription, now)
        ):
            return False

        taken = cancel_closure(self._closure_repo, self._effects, business, now)
        if taken is None:
            return False

        self._audit(business, AuditAction.DELETE, now)
        self._notices.send(business, taken, ClosureNoticeKind.REOPENED_PAID, None)
        return True

    def _audit(
        self, business: BusinessDocument, action: AuditAction, now: Microseconds
    ) -> None:
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                action=action,
                entity=CLOSURE_ENTITY,
                entity_id=AuditEntityReference(str(business.id)),
                created_at=now,
                updated_at=now,
            )
        )
