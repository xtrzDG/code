from app.containers.feedback.feedback_dependencies import FeedbackDependencies
from app.containers.feedback.feedback_use_case_factories import (
    FeedbackUseCaseFactories,
)
from app.containers.role_chain_factories import (
    business_scoped_operator,
    platform_wide_operator,
)
from app.contracts.operator_contract import OperatorContract
from app.schemas.dto.feedback.feedback_requests import (
    FeedbackRequestPage,
    FeedbackRequestPageQuery,
)
from app.schemas.dto.feedback.review_links import ReviewLinkTarget, ReviewLinkVisit
from app.schemas.dto.feedback.review_settings import (
    ReviewSettingsQuery,
    ReviewSettingsView,
    UpdateReviewSettingsCommand,
)
from app.schemas.dto.feedback.review_stats import ReviewStatsQuery, ReviewStatsView
from app.schemas.dto.jobs import JobReport, JobTick


class FeedbackOperatorFactories:
    """
    One operator per endpoint and job of the feedback context, each the
    generic role chain over one use case. The periodic job runs
    platform-wide (it walks every business that asks); the review link a
    customer opens names no business, so it runs in the caller's scope and
    the use case finds the business itself; Settings → Reviews runs in the
    business's scope.
    """

    def __init__(
        self,
        dependencies: FeedbackDependencies,
        use_cases: FeedbackUseCaseFactories,
    ) -> None:
        self._dependencies: FeedbackDependencies = dependencies
        self._use_cases: FeedbackUseCaseFactories = use_cases

    def request_visit_feedback(self) -> OperatorContract[JobTick, JobReport]:
        return platform_wide_operator(
            self._use_cases.request_visit_feedback(),
            self._dependencies.storage_scope,
        )

    def open_review_link(self) -> OperatorContract[ReviewLinkVisit, ReviewLinkTarget]:
        return business_scoped_operator(
            self._use_cases.open_review_link(), self._dependencies.storage_scope
        )

    def get_review_settings(
        self,
    ) -> OperatorContract[ReviewSettingsQuery, ReviewSettingsView]:
        return business_scoped_operator(
            self._use_cases.get_review_settings(), self._dependencies.storage_scope
        )

    def update_review_settings(
        self,
    ) -> OperatorContract[UpdateReviewSettingsCommand, ReviewSettingsView]:
        return business_scoped_operator(
            self._use_cases.update_review_settings(),
            self._dependencies.storage_scope,
        )

    def get_review_stats(self) -> OperatorContract[ReviewStatsQuery, ReviewStatsView]:
        return business_scoped_operator(
            self._use_cases.get_review_stats(), self._dependencies.storage_scope
        )

    def list_feedback_requests(
        self,
    ) -> OperatorContract[FeedbackRequestPageQuery, FeedbackRequestPage]:
        return business_scoped_operator(
            self._use_cases.list_feedback_requests(),
            self._dependencies.storage_scope,
        )
