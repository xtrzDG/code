from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.widget_visitor_use_cases import (
    WidgetVisitorUseCasesContainer,
)


class WidgetVisitorOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of a website chat visitor's uploads (one use case each)."""

    widget_visitor_use_cases: WidgetVisitorUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    admit_widget_upload_orchestrator = use_case_orchestrator(
        widget_visitor_use_cases.admit_widget_upload_use_case
    )
    accept_widget_upload_orchestrator = use_case_orchestrator(
        widget_visitor_use_cases.accept_widget_upload_use_case
    )
