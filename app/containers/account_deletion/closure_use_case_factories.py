from functools import cached_property

from app.containers.account_deletion.account_deletion_dependencies import (
    AccountDeletionDependencies,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.business_closures.closure_views import (
    BusinessClosureView,
    CancelBusinessClosureCommand,
    CloseBusinessCommand,
)
from app.schemas.dto.businesses import BusinessQuery
from app.schemas.dto.jobs import JobReport, JobTick
from app.transformers.business_closures.closure_notice_transformer import (
    ClosureNoticeTransformer,
)
from app.use_cases.businesses.closure.cancel_business_closure_use_case import (
    CancelBusinessClosureUseCase,
)
from app.use_cases.businesses.closure.close_business_use_case import (
    CloseBusinessUseCase,
)
from app.use_cases.businesses.closure.closure_effects import ClosureEffects
from app.use_cases.businesses.closure.closure_notices import ClosureNotices
from app.use_cases.businesses.closure.get_business_closure_use_case import (
    GetBusinessClosureUseCase,
)
from app.use_cases.businesses.closure.offboard_unpaid_businesses_use_case import (
    OffboardUnpaidBusinessesUseCase,
)
from app.use_cases.businesses.closure.queue_due_deletions_use_case import (
    QueueDueDeletionsUseCase,
)


class ClosureUseCaseFactories:
    """
    One typed factory per use case of a business's closure: the banner's
    view, closing, cancelling, the hourly sweep that queues due deletions
    and the daily automatic offboarding. The closure's effects and its
    notices to owners are built once and shared.
    """

    def __init__(self, dependencies: AccountDeletionDependencies) -> None:
        self._dependencies: AccountDeletionDependencies = dependencies

    @cached_property
    def effects(self) -> ClosureEffects:
        given = self._dependencies
        return ClosureEffects(
            business_repo=given.business_repo,
            channel_repo=given.channel_repo,
            subscription_repo=given.subscription_repo,
            payment_gateway=given.payment_gateway,
            payment_order_repo=given.payment_order_repo,
            remove_voice_agent=given.remove_voice_agent,
            resume_assistant=given.resume_assistant,
        )

    @cached_property
    def notices(self) -> ClosureNotices:
        given = self._dependencies
        return ClosureNotices(
            user_repo=given.user_repo,
            manager_notifier=given.manager_notifier,
            notice_transformer=ClosureNoticeTransformer(given.localized_text_resolver),
        )

    def get_business_closure(
        self,
    ) -> UseCaseContract[BusinessQuery, BusinessClosureView]:
        given = self._dependencies
        return GetBusinessClosureUseCase(
            authorize_business_access=given.authorize_business_access,
            closure_repo=given.closure_repo,
            subscription_repo=given.subscription_repo,
            brand_repo=given.brand_repo,
            user_repo=given.user_repo,
            wall_clock=given.wall_clock,
        )

    def close_business(
        self,
    ) -> UseCaseContract[CloseBusinessCommand, BusinessClosureView]:
        given = self._dependencies
        return CloseBusinessUseCase(
            authorize_business_access=given.authorize_business_access,
            step_up=given.step_up,
            closure_repo=given.closure_repo,
            deletion_repo=given.deletion_repo,
            effects=self.effects,
            notices=self.notices,
            audit_log_repo=given.audit_log_repo,
            brand_repo=given.brand_repo,
            user_repo=given.user_repo,
            wall_clock=given.wall_clock,
        )

    def cancel_business_closure(
        self,
    ) -> UseCaseContract[CancelBusinessClosureCommand, None]:
        given = self._dependencies
        return CancelBusinessClosureUseCase(
            authorize_business_access=given.authorize_business_access,
            step_up=given.step_up,
            closure_repo=given.closure_repo,
            subscription_repo=given.subscription_repo,
            effects=self.effects,
            notices=self.notices,
            audit_log_repo=given.audit_log_repo,
            wall_clock=given.wall_clock,
        )

    def queue_due_deletions(self) -> UseCaseContract[JobTick, JobReport]:
        given = self._dependencies
        return QueueDueDeletionsUseCase(
            closure_repo=given.closure_repo,
            job_queue=given.job_queue,
            job_repo=given.job_repo,
            wall_clock=given.wall_clock,
        )

    def offboard_unpaid_businesses(self) -> UseCaseContract[JobTick, JobReport]:
        given = self._dependencies
        return OffboardUnpaidBusinessesUseCase(
            business_repo=given.business_repo,
            subscription_repo=given.subscription_repo,
            invoice_repo=given.invoice_repo,
            closure_repo=given.closure_repo,
            deletion_repo=given.deletion_repo,
            effects=self.effects,
            notices=self.notices,
            audit_log_repo=given.audit_log_repo,
            offboard_after=given.app_settings.privacy.offboard_after_days,
            wall_clock=given.wall_clock,
        )
