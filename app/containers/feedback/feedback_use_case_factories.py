from app.containers.feedback.feedback_dependencies import FeedbackDependencies
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.feedback.customer_signals import CustomerSignalReply
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
from app.use_cases.feedback.answers.answer_customer_signal_use_case import (
    AnswerCustomerSignalUseCase,
)
from app.use_cases.feedback.links.open_review_link_use_case import (
    OpenReviewLinkUseCase,
)
from app.use_cases.feedback.request.request_visit_feedback_use_case import (
    RequestVisitFeedbackUseCase,
)
from app.use_cases.feedback.settings.get_review_settings_use_case import (
    GetReviewSettingsUseCase,
)
from app.use_cases.feedback.settings.get_review_stats_use_case import (
    GetReviewStatsUseCase,
)
from app.use_cases.feedback.settings.list_feedback_requests_use_case import (
    ListFeedbackRequestsUseCase,
)
from app.use_cases.feedback.settings.update_review_settings_use_case import (
    UpdateReviewSettingsUseCase,
)


class FeedbackUseCaseFactories:
    """
    The feedback context's use cases, one plain typed factory each: every
    call builds a new use case from the context's dependencies, and mypy
    checks each constructor argument.
    """

    def __init__(self, dependencies: FeedbackDependencies) -> None:
        self._dependencies: FeedbackDependencies = dependencies

    def request_visit_feedback(self) -> UseCaseContract[JobTick, JobReport]:
        """The periodic job that asks customers how their visit went."""

        given = self._dependencies
        return RequestVisitFeedbackUseCase(
            review_settings_repo=given.review_settings_repo,
            feedback_request_repo=given.feedback_request_repo,
            business_repo=given.business_repo,
            booking_repo=given.booking_repo,
            contact_repo=given.contact_repo,
            channel_repo=given.channel_repo,
            conversation_repo=given.conversation_repo,
            message_repo=given.message_repo,
            outbound_message_repo=given.outbound_message_repo,
            job_queue=given.job_queue,
            rate_limits=given.rate_limits,
            text_resolver=given.text_resolver,
            live_events=given.live_events,
            wall_clock=given.wall_clock,
            suppression_list=given.suppression_list,
        )

    def answer_customer_signal(
        self,
    ) -> UseCaseContract[PreparedTurn, CustomerSignalReply | None]:
        """The platform's answers to STOP, START and a rating."""

        given = self._dependencies
        return AnswerCustomerSignalUseCase(
            contact_repo=given.contact_repo,
            audit_log_repo=given.audit_log_repo,
            feedback_request_repo=given.feedback_request_repo,
            message_repo=given.message_repo,
            profile_repo=given.business_profile_repo,
            text_resolver=given.text_resolver,
            wall_clock=given.wall_clock,
            app_base_url=given.app_base_url,
            suppression_list=given.suppression_list,
        )

    def open_review_link(self) -> UseCaseContract[ReviewLinkVisit, ReviewLinkTarget]:
        given = self._dependencies
        return OpenReviewLinkUseCase(
            feedback_request_repo=given.feedback_request_repo,
            profile_repo=given.business_profile_repo,
            storage_scope=given.storage_scope,
            wall_clock=given.wall_clock,
        )

    def get_review_settings(
        self,
    ) -> UseCaseContract[ReviewSettingsQuery, ReviewSettingsView]:
        given = self._dependencies
        return GetReviewSettingsUseCase(
            authorize_business_access=given.authorize_business_access,
            review_settings_repo=given.review_settings_repo,
            profile_repo=given.business_profile_repo,
            channel_repo=given.channel_repo,
            text_resolver=given.text_resolver,
            app_base_url=given.app_base_url,
        )

    def update_review_settings(
        self,
    ) -> UseCaseContract[UpdateReviewSettingsCommand, ReviewSettingsView]:
        given = self._dependencies
        return UpdateReviewSettingsUseCase(
            authorize_business_access=given.authorize_business_access,
            review_settings_repo=given.review_settings_repo,
            profile_repo=given.business_profile_repo,
            channel_repo=given.channel_repo,
            audit_log_repo=given.audit_log_repo,
            text_resolver=given.text_resolver,
            wall_clock=given.wall_clock,
            app_base_url=given.app_base_url,
        )

    def get_review_stats(self) -> UseCaseContract[ReviewStatsQuery, ReviewStatsView]:
        given = self._dependencies
        return GetReviewStatsUseCase(
            authorize_business_access=given.authorize_business_access,
            feedback_request_repo=given.feedback_request_repo,
            wall_clock=given.wall_clock,
        )

    def list_feedback_requests(
        self,
    ) -> UseCaseContract[FeedbackRequestPageQuery, FeedbackRequestPage]:
        given = self._dependencies
        return ListFeedbackRequestsUseCase(
            authorize_business_access=given.authorize_business_access,
            feedback_request_repo=given.feedback_request_repo,
            contact_repo=given.contact_repo,
            audit_log_repo=given.audit_log_repo,
            wall_clock=given.wall_clock,
        )
