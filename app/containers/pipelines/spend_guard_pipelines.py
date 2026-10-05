from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.spend_guard_orchestrators import (
    SpendGuardOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class SpendGuardPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the spend guard's endpoints."""

    spend_guard: SpendGuardOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    admit_api_request_pipeline = orchestrator_pipeline(
        spend_guard.admit_api_request_orchestrator
    )
    check_widget_origin_pipeline = orchestrator_pipeline(
        spend_guard.check_widget_origin_orchestrator
    )
    get_widget_allowed_origins_pipeline = orchestrator_pipeline(
        spend_guard.get_widget_allowed_origins_orchestrator
    )
    save_widget_allowed_origins_pipeline = orchestrator_pipeline(
        spend_guard.save_widget_allowed_origins_orchestrator
    )
    get_platform_spend_pipeline = orchestrator_pipeline(
        spend_guard.get_platform_spend_orchestrator
    )
    set_business_spend_limits_pipeline = orchestrator_pipeline(
        spend_guard.set_business_spend_limits_orchestrator
    )
