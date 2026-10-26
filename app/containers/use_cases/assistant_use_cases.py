from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Dependency, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.conversation_use_cases import (
    ConversationUseCasesContainer,
)
from app.containers.use_cases.launch_use_cases import LaunchUseCasesContainer
from app.containers.use_cases.pending_change_use_cases import (
    PendingChangeUseCasesContainer,
)
from app.containers.use_cases.voice_use_cases import VoiceUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.assistants.assembly_sources import AssistantVersionActivation
from app.schemas.dto.assistants.assistant_commands import (
    AssembleAssistantVersionCommand,
    AssistantVersionQuery,
    AssistantVersionsQuery,
    PublishAssistantVersionCommand,
    RollbackAssistantVersionCommand,
)
from app.schemas.dto.assistants.assistant_views import (
    AssistantVersionDetails,
    AssistantVersionSummary,
)
from app.schemas.dto.businesses import (
    BusinessView,
    UpdateBusinessSettingsCommand,
)
from app.schemas.dto.go_live import GoLiveReadiness, GoLiveReadinessRequest
from app.use_cases.assistants.activate_assistant_version_use_case import (
    ActivateAssistantVersionUseCase,
)
from app.use_cases.assistants.assemble_assistant_version_use_case import (
    AssembleAssistantVersionUseCase,
)
from app.use_cases.assistants.check_go_live_readiness_use_case import (
    CheckGoLiveReadinessUseCase,
)
from app.use_cases.assistants.get_assistant_version_use_case import (
    GetAssistantVersionUseCase,
)
from app.use_cases.assistants.get_go_live_readiness_use_case import (
    GetGoLiveReadinessUseCase,
)
from app.use_cases.assistants.list_assistant_versions_use_case import (
    ListAssistantVersionsUseCase,
)
from app.use_cases.assistants.publish_assistant_version_use_case import (
    PublishAssistantVersionUseCase,
)
from app.use_cases.assistants.resume_assistant_use_case import (
    ResumeAssistantUseCase,
)
from app.use_cases.assistants.rollback_assistant_version_use_case import (
    RollbackAssistantVersionUseCase,
)
from app.use_cases.businesses.update_business_settings_use_case import (
    UpdateBusinessSettingsUseCase,
)


class AssistantUseCasesContainer(containers.DeclarativeContainer):
    """
    Assistant versions: assembly, go-live readiness, activation, publishing and
    rollback. Business settings live here too: a settings change resumes or
    pauses the live assistant.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    conversation_use_cases: ConversationUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    voice_use_cases: VoiceUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    launch_use_cases: LaunchUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    pending_change_use_cases: PendingChangeUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    # Assembly queues `index_knowledge` (aliases and search vectors).
    job_queue: Dependency[JobQueueFacilitator] = Dependency(
        instance_of=JobQueueFacilitator
    )

    assemble_assistant_version_use_case: Factory[
        UseCaseContract[AssembleAssistantVersionCommand, AssistantVersionDetails]
    ] = Factory(
        AssembleAssistantVersionUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        business_repo=repositories.business_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        build_assistant_draft=pending_change_use_cases.build_assistant_draft_use_case,
        version_details_transformer=transformers.assistant_version_details_transformer,
        app_settings=config.app_settings,
        job_queue=job_queue,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_assistant_versions_use_case: Factory[
        UseCaseContract[AssistantVersionsQuery, list[AssistantVersionSummary]]
    ] = Factory(
        ListAssistantVersionsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        assistant_version_repo=repositories.assistant_version_repo,
        version_summary_transformer=transformers.assistant_version_summary_transformer,
    )
    get_assistant_version_use_case: Factory[
        UseCaseContract[AssistantVersionQuery, AssistantVersionDetails]
    ] = Factory(
        GetAssistantVersionUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        assistant_version_repo=repositories.assistant_version_repo,
        version_details_transformer=transformers.assistant_version_details_transformer,
    )
    check_go_live_readiness_use_case: Factory[
        UseCaseContract[GoLiveReadinessRequest, GoLiveReadiness]
    ] = Factory(
        CheckGoLiveReadinessUseCase,
        subscription_repo=repositories.subscription_repo,
        dpa_acceptance_repo=repositories.dpa_acceptance_repo,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        brand_knowledge_item_repo=repositories.brand_knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        niche_template_registry=registries.niche_template_registry,
        plan_registry=registries.plan_registry,
        voice_agent_provisioner=adapters.voice_agent_provisioner,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_go_live_readiness_use_case: Factory[
        UseCaseContract[AssistantVersionQuery, GoLiveReadiness]
    ] = Factory(
        GetGoLiveReadinessUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        assistant_version_repo=repositories.assistant_version_repo,
        check_go_live_readiness=check_go_live_readiness_use_case,
    )
    activate_assistant_version_use_case: Factory[
        UseCaseContract[AssistantVersionActivation, AssistantVersionDocument]
    ] = Factory(
        ActivateAssistantVersionUseCase,
        check_go_live_readiness=check_go_live_readiness_use_case,
        remove_voice_agent=voice_use_cases.remove_voice_agent_use_case,
        business_repo=repositories.business_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        voice_agent_provisioner=adapters.voice_agent_provisioner,
        voice_agent_sources=voice_use_cases.voice_agent_sources,
        start_trial_at_go_live=launch_use_cases.start_trial_at_go_live_use_case,
        record_activation_event=launch_use_cases.record_activation_event_use_case,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
        voice_agent_locks=registries.voice_agent_lock_registry,
        closure_repo=repositories.business_closure_repo,
    )
    resume_assistant_use_case: Factory[UseCaseContract[BusinessDocument, None]] = (
        Factory(
            ResumeAssistantUseCase,
            assistant_version_repo=repositories.assistant_version_repo,
            activate_assistant_version=activate_assistant_version_use_case,
        )
    )
    update_business_settings_use_case: Factory[
        UseCaseContract[UpdateBusinessSettingsCommand, BusinessView]
    ] = Factory(
        UpdateBusinessSettingsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        brand_repo=repositories.brand_repo,
        subscription_repo=repositories.subscription_repo,
        language_registry=registries.language_registry,
        phone_number_parser=utilities.phone_number_parser,
        audit_log_repo=repositories.audit_log_repo,
        business_view_transformer=transformers.business_view_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
        remove_voice_agent=voice_use_cases.remove_voice_agent_use_case,
        resume_assistant=resume_assistant_use_case,
        closure_repo=repositories.business_closure_repo,
    )
    publish_assistant_version_use_case: Factory[
        UseCaseContract[PublishAssistantVersionCommand, AssistantVersionDetails]
    ] = Factory(
        PublishAssistantVersionUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        assistant_version_repo=repositories.assistant_version_repo,
        check_go_live_readiness=check_go_live_readiness_use_case,
        activate_assistant_version=activate_assistant_version_use_case,
        version_details_transformer=transformers.assistant_version_details_transformer,
        user_repo=repositories.user_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        closure_repo=repositories.business_closure_repo,
    )
    rollback_assistant_version_use_case: Factory[
        UseCaseContract[RollbackAssistantVersionCommand, AssistantVersionDetails]
    ] = Factory(
        RollbackAssistantVersionUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        assistant_version_repo=repositories.assistant_version_repo,
        activate_assistant_version=activate_assistant_version_use_case,
        version_details_transformer=transformers.assistant_version_details_transformer,
    )
