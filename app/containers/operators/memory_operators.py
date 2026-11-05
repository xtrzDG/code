from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.memory_pipelines import MemoryPipelinesContainer
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class MemoryOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the customer memory, each in its business's scope: Settings
    → General's switch and the summary job (the queued job names its
    business).
    """

    memory_pipelines: MemoryPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    get_assistant_settings_operator = pipeline_operator(
        memory_pipelines.get_assistant_settings_pipeline, storage_scope
    )
    update_assistant_settings_operator = pipeline_operator(
        memory_pipelines.update_assistant_settings_pipeline, storage_scope
    )
    summarize_conversation_operator = pipeline_operator(
        memory_pipelines.summarize_conversation_pipeline, storage_scope
    )
