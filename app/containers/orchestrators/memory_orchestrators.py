from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.memory_use_cases import MemoryUseCasesContainer


class MemoryOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of the customer memory (one use case each)."""

    memory_use_cases: MemoryUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_assistant_settings_orchestrator = use_case_orchestrator(
        memory_use_cases.get_assistant_settings_use_case
    )
    update_assistant_settings_orchestrator = use_case_orchestrator(
        memory_use_cases.update_assistant_settings_use_case
    )
    summarize_conversation_orchestrator = use_case_orchestrator(
        memory_use_cases.summarize_conversation_use_case
    )
