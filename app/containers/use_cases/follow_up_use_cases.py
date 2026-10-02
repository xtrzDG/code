from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.bookings import (
    CreateLeadCommand,
    LeadView,
)
from app.schemas.dto.handoffs import (
    HandoffCommand,
    HandoffResult,
    RecordUnansweredQuestionCommand,
    UnansweredQuestionView,
)
from app.schemas.dto.operations import (
    AnsweredQuestionResult,
    AnswerUnansweredQuestionCommand,
    DashboardStats,
    DashboardStatsQuery,
    HandoffListItem,
    HandoffPage,
    LeadPage,
    ListHandoffsQuery,
    ListLeadsQuery,
    ListUnansweredQuestionsQuery,
    ResolveHandoffCommand,
    UnansweredQuestionPage,
    UpdateLeadStatusCommand,
)
from app.use_cases.handoffs.answer_unanswered_question_use_case import (
    AnswerUnansweredQuestionUseCase,
)
from app.use_cases.handoffs.handoff_to_human_use_case import HandoffToHumanUseCase
from app.use_cases.handoffs.list_handoffs_use_case import ListHandoffsUseCase
from app.use_cases.handoffs.list_unanswered_questions_use_case import (
    ListUnansweredQuestionsUseCase,
)
from app.use_cases.handoffs.record_unanswered_question_use_case import (
    RecordUnansweredQuestionUseCase,
)
from app.use_cases.handoffs.resolve_handoff_use_case import ResolveHandoffUseCase
from app.use_cases.insights.get_dashboard_stats_use_case import GetDashboardStatsUseCase
from app.use_cases.leads.create_lead_use_case import CreateLeadUseCase
from app.use_cases.leads.list_leads_use_case import ListLeadsUseCase
from app.use_cases.leads.update_lead_status_use_case import UpdateLeadStatusUseCase


class FollowUpUseCasesContainer(containers.DeclarativeContainer):
    """
    What the assistant leaves for staff to follow up: leads, handoffs to a
    human, unanswered questions, and the dashboard that counts the work.
    """

    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    create_lead_use_case: Factory[UseCaseContract[CreateLeadCommand, LeadView]] = (
        Factory(
            CreateLeadUseCase,
            business_repo=repositories.business_repo,
            lead_repo=repositories.lead_repo,
            contact_repo=repositories.contact_repo,
            audit_log_repo=repositories.audit_log_repo,
            phone_number_parser=utilities.phone_number_parser,
            staff_notification_transformer=transformers.new_lead_notification_transformer,
            manager_broadcaster=facilitators.manager_broadcast_facilitator,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    list_leads_use_case: Factory[UseCaseContract[ListLeadsQuery, LeadPage]] = Factory(
        ListLeadsUseCase,
        business_repo=repositories.business_repo,
        lead_repo=repositories.lead_repo,
        contact_repo=repositories.contact_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    update_lead_status_use_case: Factory[
        UseCaseContract[UpdateLeadStatusCommand, LeadView]
    ] = Factory(
        UpdateLeadStatusUseCase,
        lead_repo=repositories.lead_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    handoff_to_human_use_case: Factory[
        UseCaseContract[HandoffCommand, HandoffResult]
    ] = Factory(
        HandoffToHumanUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        conversation_repo=repositories.conversation_repo,
        contact_repo=repositories.contact_repo,
        handoff_repo=repositories.handoff_repo,
        phone_number_parser=utilities.phone_number_parser,
        staff_notification_transformer=transformers.handoff_notification_transformer,
        customer_message_transformer=transformers.handoff_customer_message_transformer,
        manager_broadcaster=facilitators.manager_broadcast_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    resolve_handoff_use_case: Factory[
        UseCaseContract[ResolveHandoffCommand, HandoffListItem]
    ] = Factory(
        ResolveHandoffUseCase,
        handoff_repo=repositories.handoff_repo,
        conversation_repo=repositories.conversation_repo,
        contact_repo=repositories.contact_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_handoffs_use_case: Factory[UseCaseContract[ListHandoffsQuery, HandoffPage]] = (
        Factory(
            ListHandoffsUseCase,
            business_repo=repositories.business_repo,
            handoff_repo=repositories.handoff_repo,
            contact_repo=repositories.contact_repo,
            audit_log_repo=repositories.audit_log_repo,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    record_unanswered_question_use_case: Factory[
        UseCaseContract[RecordUnansweredQuestionCommand, UnansweredQuestionView]
    ] = Factory(
        RecordUnansweredQuestionUseCase,
        business_repo=repositories.business_repo,
        unanswered_question_repo=repositories.unanswered_question_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_unanswered_questions_use_case: Factory[
        UseCaseContract[ListUnansweredQuestionsQuery, UnansweredQuestionPage]
    ] = Factory(
        ListUnansweredQuestionsUseCase,
        unanswered_question_repo=repositories.unanswered_question_repo,
    )
    answer_unanswered_question_use_case: Factory[
        UseCaseContract[AnswerUnansweredQuestionCommand, AnsweredQuestionResult]
    ] = Factory(
        AnswerUnansweredQuestionUseCase,
        unanswered_question_repo=repositories.unanswered_question_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_dashboard_stats_use_case: Factory[
        UseCaseContract[DashboardStatsQuery, DashboardStats]
    ] = Factory(
        GetDashboardStatsUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        booking_repo=repositories.booking_repo,
        lead_repo=repositories.lead_repo,
        handoff_repo=repositories.handoff_repo,
        unanswered_question_repo=repositories.unanswered_question_repo,
        usage_event_repo=repositories.usage_event_repo,
        subscription_repo=repositories.subscription_repo,
        plan_registry=registries.plan_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
