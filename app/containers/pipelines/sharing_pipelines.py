from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.orchestrators.sharing_orchestrators import (
    SharingOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline
from app.containers.registries import RegistriesContainer
from app.contracts.pipeline_contract import PipelineContract
from app.pipelines.widget.widget_handoff_pipeline import WidgetHandoffPipeline
from app.schemas.dto.channels.widget_handoff import (
    WidgetHandoffCommand,
    WidgetHandoffView,
)


class SharingPipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines of sharing the assistant; "Talk to a person" holds the
    visitor's customer lock, like the visitor's messages.
    """

    sharing_orchestrators: SharingOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_share_links_pipeline = orchestrator_pipeline(
        sharing_orchestrators.get_share_links_orchestrator
    )
    set_public_slug_pipeline = orchestrator_pipeline(
        sharing_orchestrators.set_public_slug_orchestrator
    )
    hosted_chat_pipeline = orchestrator_pipeline(
        sharing_orchestrators.hosted_chat_orchestrator
    )
    widget_handoff_pipeline: Factory[
        PipelineContract[WidgetHandoffCommand, WidgetHandoffView]
    ] = Factory(
        WidgetHandoffPipeline,
        widget_handoff_orchestrator=sharing_orchestrators.widget_handoff_orchestrator,
        customer_locks=registries.customer_message_lock_registry,
    )
    open_widget_stream_pipeline = orchestrator_pipeline(
        sharing_orchestrators.open_widget_stream_orchestrator
    )
    read_widget_stream_message_pipeline = orchestrator_pipeline(
        sharing_orchestrators.read_widget_stream_message_orchestrator
    )
