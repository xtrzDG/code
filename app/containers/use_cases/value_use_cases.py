from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.value.conversation_topics import (
    ConversationTopicsQuery,
    ConversationTopicsView,
)
from app.schemas.dto.value.customer_sources import (
    CustomerSourcesQuery,
    CustomerSourcesView,
)
from app.schemas.dto.value.value_model import ValueModel, ValueModelQuery
from app.schemas.dto.value.value_reports import (
    ValueReportPage,
    ValueReportPageQuery,
    ValueReportQuery,
    ValueReportView,
)
from app.schemas.dto.value.value_views import (
    BusinessValueQuery,
    DigestPreferencesQuery,
    DigestPreferencesView,
    TodayQueue,
    TodayQueueQuery,
    UpdateDigestPreferencesCommand,
    UpdateValueSettingsCommand,
    ValueSettingsQuery,
    ValueSettingsView,
)
from app.use_cases.insights.topics.get_conversation_topics_use_case import (
    GetConversationTopicsUseCase,
)
from app.use_cases.insights.topics.group_conversation_topics_use_case import (
    GroupConversationTopicsUseCase,
)
from app.use_cases.insights.value.compute_value_model_use_case import (
    ComputeValueModelUseCase,
)
from app.use_cases.insights.value.get_business_value_use_case import (
    GetBusinessValueUseCase,
)
from app.use_cases.insights.value.get_customer_sources_use_case import (
    GetCustomerSourcesUseCase,
)
from app.use_cases.insights.value.get_digest_preferences_use_case import (
    GetDigestPreferencesUseCase,
)
from app.use_cases.insights.value.get_today_queue_use_case import (
    GetTodayQueueUseCase,
)
from app.use_cases.insights.value.get_value_report_use_case import (
    GetValueReportUseCase,
)
from app.use_cases.insights.value.get_value_settings_use_case import (
    GetValueSettingsUseCase,
)
from app.use_cases.insights.value.list_value_reports_use_case import (
    ListValueReportsUseCase,
)
from app.use_cases.insights.value.send_value_reports_use_case import (
    SendValueReportsUseCase,
)
from app.use_cases.insights.value.update_digest_preferences_use_case import (
    UpdateDigestPreferencesUseCase,
)
from app.use_cases.insights.value.update_value_settings_use_case import (
    UpdateValueSettingsUseCase,
)
from app.use_cases.insights.value.value_counting import ValueSources
from app.use_cases.insights.value.value_estimates import EstimateCatalogs
from app.use_cases.insights.value.value_return import PlanPrices


class ValueUseCasesContainer(containers.DeclarativeContainer):
    """
    What the assistant is worth to a business: the value model of a period
    (one computation for the dashboard, the digests and the monthly
    report), the average check, each owner's digest choices, the stored
    reports, today's queue, and the hourly job that sends the digests;
    where customers came from and what they ask about (the nightly topics).
    """

    adapters: AdaptersContainer = composed_container_edge(AdaptersContainer)  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    authorize = account_use_cases.authorize_business_access_use_case
    wall_clock = time_provider.microsecond_wall_clock

    value_sources: Factory[ValueSources] = Factory(
        ValueSources,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        booking_repo=repositories.booking_repo,
        lead_repo=repositories.lead_repo,
        handoff_repo=repositories.handoff_repo,
        value_count_repo=repositories.value_count_repo,
    )
    estimate_catalogs: Factory[EstimateCatalogs] = Factory(
        EstimateCatalogs,
        niche_value_registry=registries.niche_value_registry,
        niche_template_registry=registries.niche_template_registry,
        exchange_rate_registry=registries.exchange_rate_registry,
        value_settings_repo=repositories.value_settings_repo,
    )
    plan_prices: Factory[PlanPrices] = Factory(
        PlanPrices,
        subscription_repo=repositories.subscription_repo,
        plan_registry=registries.plan_registry,
    )
    compute_value_model_use_case: Factory[
        UseCaseContract[ValueModelQuery, ValueModel]
    ] = Factory(
        ComputeValueModelUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        sources=value_sources,
        catalogs=estimate_catalogs,
        plan_prices=plan_prices,
    )
    get_business_value_use_case: Factory[
        UseCaseContract[BusinessValueQuery, ValueModel]
    ] = Factory(
        GetBusinessValueUseCase,
        authorize_business_access=authorize,
        compute_value_model=compute_value_model_use_case,
        activation_event_repo=repositories.activation_event_repo,
        wall_clock=wall_clock,
    )
    get_value_settings_use_case: Factory[
        UseCaseContract[ValueSettingsQuery, ValueSettingsView]
    ] = Factory(
        GetValueSettingsUseCase,
        authorize_business_access=authorize,
        catalogs=estimate_catalogs,
    )
    update_value_settings_use_case: Factory[
        UseCaseContract[UpdateValueSettingsCommand, ValueSettingsView]
    ] = Factory(
        UpdateValueSettingsUseCase,
        authorize_business_access=authorize,
        catalogs=estimate_catalogs,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
    get_digest_preferences_use_case: Factory[
        UseCaseContract[DigestPreferencesQuery, DigestPreferencesView]
    ] = Factory(
        GetDigestPreferencesUseCase,
        authorize_business_access=authorize,
        digest_preferences_repo=repositories.digest_preferences_repo,
        user_repo=repositories.user_repo,
        push_subscription_repo=repositories.push_subscription_repo,
        app_settings=config.app_settings,
    )
    update_digest_preferences_use_case: Factory[
        UseCaseContract[UpdateDigestPreferencesCommand, DigestPreferencesView]
    ] = Factory(
        UpdateDigestPreferencesUseCase,
        authorize_business_access=authorize,
        digest_preferences_repo=repositories.digest_preferences_repo,
        user_repo=repositories.user_repo,
        push_subscription_repo=repositories.push_subscription_repo,
        audit_log_repo=repositories.audit_log_repo,
        app_settings=config.app_settings,
        wall_clock=wall_clock,
    )
    list_value_reports_use_case: Factory[
        UseCaseContract[ValueReportPageQuery, ValueReportPage]
    ] = Factory(
        ListValueReportsUseCase,
        authorize_business_access=authorize,
        value_report_repo=repositories.value_report_repo,
    )
    get_value_report_use_case: Factory[
        UseCaseContract[ValueReportQuery, ValueReportView]
    ] = Factory(
        GetValueReportUseCase,
        authorize_business_access=authorize,
        value_report_repo=repositories.value_report_repo,
    )
    get_today_queue_use_case: Factory[UseCaseContract[TodayQueueQuery, TodayQueue]] = (
        Factory(
            GetTodayQueueUseCase,
            authorize_business_access=authorize,
            value_count_repo=repositories.value_count_repo,
            wall_clock=wall_clock,
        )
    )
    # The hourly job of the digests and monthly reports (platform-wide).
    send_value_reports_use_case: Factory[UseCaseContract[JobTick, JobReport]] = Factory(
        SendValueReportsUseCase,
        business_repo=repositories.business_repo,
        value_report_repo=repositories.value_report_repo,
        digest_preferences_repo=repositories.digest_preferences_repo,
        compute_value_model=compute_value_model_use_case,
        owner_digests=facilitators.owner_digest_facilitator,
        wall_clock=wall_clock,
    )
    get_customer_sources_use_case: Factory[
        UseCaseContract[CustomerSourcesQuery, CustomerSourcesView]
    ] = Factory(
        GetCustomerSourcesUseCase,
        authorize_business_access=authorize,
        customer_source_repo=repositories.customer_source_repo,
        catalogs=estimate_catalogs,
        wall_clock=wall_clock,
    )
    get_conversation_topics_use_case: Factory[
        UseCaseContract[ConversationTopicsQuery, ConversationTopicsView]
    ] = Factory(
        GetConversationTopicsUseCase,
        authorize_business_access=authorize,
        conversation_topics_repo=repositories.conversation_topics_repo,
    )
    # The hourly job that groups the topics once a night (platform-wide).
    group_conversation_topics_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            GroupConversationTopicsUseCase,
            business_repo=repositories.business_repo,
            conversation_topics_repo=repositories.conversation_topics_repo,
            topic_input_repo=repositories.topic_input_repo,
            unanswered_question_repo=repositories.unanswered_question_repo,
            llm_adapter=adapters.llm_adapter,
            app_settings=config.app_settings,
            wall_clock=wall_clock,
        )
    )
