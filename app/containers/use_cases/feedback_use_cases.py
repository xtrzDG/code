from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
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


class FeedbackUseCasesContainer(containers.DeclarativeContainer):
    """
    Feedback after visits: the periodic job that asks customers how their
    visit went, the platform's answers to STOP, START and a rating, the
    review link a customer opens, and Settings → Reviews.
    """

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    app_base_url = config.app_settings.provided.app_base_url

    request_visit_feedback_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            RequestVisitFeedbackUseCase,
            review_settings_repo=repositories.review_settings_repo,
            feedback_request_repo=repositories.feedback_request_repo,
            business_repo=repositories.business_repo,
            booking_repo=repositories.booking_repo,
            contact_repo=repositories.contact_repo,
            channel_repo=repositories.channel_repo,
            conversation_repo=repositories.conversation_repo,
            message_repo=repositories.message_repo,
            outbound_message_repo=repositories.outbound_message_repo,
            job_queue=facilitators.job_queue_facilitator,
            rate_limits=registries.request_rate_limit_registry,
            text_resolver=utilities.localized_text_resolver,
            live_events=facilitators.event_publisher,
            wall_clock=time_provider.microsecond_wall_clock,
            suppression_list=facilitators.suppression_list,
        )
    )
    answer_customer_signal_use_case: Factory[
        UseCaseContract[PreparedTurn, CustomerSignalReply | None]
    ] = Factory(
        AnswerCustomerSignalUseCase,
        contact_repo=repositories.contact_repo,
        audit_log_repo=repositories.audit_log_repo,
        feedback_request_repo=repositories.feedback_request_repo,
        message_repo=repositories.message_repo,
        profile_repo=repositories.business_profile_repo,
        text_resolver=utilities.localized_text_resolver,
        wall_clock=time_provider.microsecond_wall_clock,
        app_base_url=app_base_url,
        suppression_list=facilitators.suppression_list,
    )
    open_review_link_use_case: Factory[
        UseCaseContract[ReviewLinkVisit, ReviewLinkTarget]
    ] = Factory(
        OpenReviewLinkUseCase,
        feedback_request_repo=repositories.feedback_request_repo,
        profile_repo=repositories.business_profile_repo,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )

    # --- Settings → Reviews (owners).
    get_review_settings_use_case: Factory[
        UseCaseContract[ReviewSettingsQuery, ReviewSettingsView]
    ] = Factory(
        GetReviewSettingsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        review_settings_repo=repositories.review_settings_repo,
        profile_repo=repositories.business_profile_repo,
        channel_repo=repositories.channel_repo,
        text_resolver=utilities.localized_text_resolver,
        app_base_url=app_base_url,
    )
    update_review_settings_use_case: Factory[
        UseCaseContract[UpdateReviewSettingsCommand, ReviewSettingsView]
    ] = Factory(
        UpdateReviewSettingsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        review_settings_repo=repositories.review_settings_repo,
        profile_repo=repositories.business_profile_repo,
        channel_repo=repositories.channel_repo,
        audit_log_repo=repositories.audit_log_repo,
        text_resolver=utilities.localized_text_resolver,
        wall_clock=time_provider.microsecond_wall_clock,
        app_base_url=app_base_url,
    )
    get_review_stats_use_case: Factory[
        UseCaseContract[ReviewStatsQuery, ReviewStatsView]
    ] = Factory(
        GetReviewStatsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        feedback_request_repo=repositories.feedback_request_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_feedback_requests_use_case: Factory[
        UseCaseContract[FeedbackRequestPageQuery, FeedbackRequestPage]
    ] = Factory(
        ListFeedbackRequestsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        feedback_request_repo=repositories.feedback_request_repo,
        contact_repo=repositories.contact_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
