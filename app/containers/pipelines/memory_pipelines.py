from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.memory_orchestrators import (
    MemoryOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class MemoryPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the customer memory."""

    memory: MemoryOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    get_assistant_settings_pipeline = orchestrator_pipeline(
        memory.get_assistant_settings_orchestrator
    )
    update_assistant_settings_pipeline = orchestrator_pipeline(
        memory.update_assistant_settings_orchestrator
    )
    summarize_conversation_pipeline = orchestrator_pipeline(
        memory.summarize_conversation_orchestrator
    )
