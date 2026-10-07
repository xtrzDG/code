from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.sharing_pipelines import SharingPipelinesContainer
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class SharingOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of sharing the assistant. The hosted chat page's input names
    no business (it is found from the page's address), so its operator runs
    unscoped and the orchestrator enters the business's scope itself.
    """

    sharing_pipelines: SharingPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # Operators run inside the storage scope of the business they serve.
    storage_scope = utilities.storage_scope

    get_share_links_operator = pipeline_operator(
        sharing_pipelines.get_share_links_pipeline, storage_scope
    )
    set_public_slug_operator = pipeline_operator(
        sharing_pipelines.set_public_slug_pipeline, storage_scope
    )
    hosted_chat_operator = pipeline_operator(
        sharing_pipelines.hosted_chat_pipeline, storage_scope
    )
    widget_handoff_operator = pipeline_operator(
        sharing_pipelines.widget_handoff_pipeline, storage_scope
    )
    # The website chat's live stream (in the scope of the business it names).
    open_widget_stream_operator = pipeline_operator(
        sharing_pipelines.open_widget_stream_pipeline, storage_scope
    )
    read_widget_stream_message_operator = pipeline_operator(
        sharing_pipelines.read_widget_stream_message_pipeline, storage_scope
    )
