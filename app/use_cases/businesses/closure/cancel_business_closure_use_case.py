from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.business_closures import (
    BusinessClosureReason,
    ClosureNoticeKind,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.business_closures import BusinessClosureDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.business_closures.closure_views import (
    CancelBusinessClosureCommand,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.use_cases.businesses.closure.close_business_use_case import CLOSURE_ENTITY
from app.use_cases.businesses.closure.closure_cancellation import cancel_closure
from app.use_cases.businesses.closure.closure_effects import ClosureEffects
from app.use_cases.businesses.closure.closure_notices import ClosureNotices
from app.use_cases.businesses.closure.closure_reads import is_paid_for


class CancelBusinessClosureUseCase(UseCaseContract[CancelBusinessClosureCommand, None]):
    """
    An owner cancels the closure (after a fresh sign-in) while the deletion
    has not begun: the business is back as it was, the channels the
    closure turned off on again and a live assistant resumed; billing
    stays stopped until a plan is chosen again. A closure for non-payment
    is cancelled by paying (the offboarding job then cancels it too), so
    cancelling it before is refused. Only one request removes the closure:
    the closure is taken in one atomic step, so two cancels restore once.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        step_up: StepUpGuardContract,
        closure_repo: BusinessClosureRepoContract,
        subscription_repo: SubscriptionRepoContract,
        effects: ClosureEffects,
        notices: ClosureNotices,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._step_up: StepUpGuardContract = step_up
        self._closure_repo: BusinessClosureRepoContract = closure_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._effects: ClosureEffects = effects
        self._notices: ClosureNotices = notices
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CancelBusinessClosureCommand) -> None:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        self._step_up.require_recent_authentication()
        now: Microseconds = self._wall_clock.now_unix()
        closure: BusinessClosureDocument | None = self._closure_repo.get(business.id)
        if closure is None:
            raise NotFoundError("The business is not closing.")

        if (
            closure.reason is BusinessClosureReason.UNPAID_SUBSCRIPTION
            and not is_paid_for(self._subscription_repo, business, now)
        ):
            raise ConflictError(
                "The business closed because its subscription ended unpaid: pay "
                "in Billing to keep it."
            )

        taken: BusinessClosureDocument | None = cancel_closure(
            self._closure_repo, self._effects, business, now
        )
        if taken is None:
            raise ConflictError("The deletion has begun and cannot be stopped.")

        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.DELETE,
                entity=CLOSURE_ENTITY,
                entity_id=AuditEntityReference(str(business.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        self._notices.send(
            business, taken, ClosureNoticeKind.CANCELLED, input_data.user_id
        )
