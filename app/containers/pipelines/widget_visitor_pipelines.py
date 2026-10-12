from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.widget_visitor_orchestrators import (
    WidgetVisitorOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class WidgetVisitorPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of a website chat visitor's uploads."""

    orchestrators: WidgetVisitorOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    admit_widget_upload_pipeline = orchestrator_pipeline(
        orchestrators.admit_widget_upload_orchestrator
    )
    accept_widget_upload_pipeline = orchestrator_pipeline(
        orchestrators.accept_widget_upload_orchestrator
    )
