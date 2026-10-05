from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.customer_memory.assistant_settings import (
    AssistantSettingsCommand,
    AssistantSettingsQuery,
    AssistantSettingsView,
)
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.use_cases.conversations.memory.get_assistant_settings_use_case import (
    GetAssistantSettingsUseCase,
)
from app.use_cases.conversations.memory.summarize_conversation_use_case import (
    SummarizeConversationUseCase,
)
from app.use_cases.conversations.memory.update_assistant_settings_use_case import (
    UpdateAssistantSettingsUseCase,
)


class MemoryUseCasesContainer(containers.DeclarativeContainer):
    """
    The customer memory (1121): Settings → General's switch, and the queued
    job that writes a conversation's summary once it is quiet. What a turn
    recalls is part of the conversation engine (`ConversationUseCasesContainer`).
    """

    adapters: AdaptersContainer = composed_container_edge(AdaptersContainer)  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_assistant_settings_use_case: Factory[
        UseCaseContract[AssistantSettingsQuery, AssistantSettingsView]
    ] = Factory(
        GetAssistantSettingsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        assistant_settings_repo=repositories.assistant_settings_repo,
    )
    update_assistant_settings_use_case: Factory[
        UseCaseContract[AssistantSettingsCommand, AssistantSettingsView]
    ] = Factory(
        UpdateAssistantSettingsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        assistant_settings_repo=repositories.assistant_settings_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    summarize_conversation_use_case: Factory[
        UseCaseContract[QueuedJobInput, JobReport]
    ] = Factory(
        SummarizeConversationUseCase,
        business_repo=repositories.business_repo,
        conversation_repo=repositories.conversation_repo,
        conversation_memory_repo=repositories.conversation_repo,
        contact_repo=repositories.contact_repo,
        message_repo=repositories.message_repo,
        assistant_settings_repo=repositories.assistant_settings_repo,
        job_queue=facilitators.job_queue_facilitator,
        llm_adapter=adapters.llm_adapter,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
