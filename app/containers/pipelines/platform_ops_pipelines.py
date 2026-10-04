from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.platform_ops_orchestrators import (
    PlatformOpsOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class PlatformOpsPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the platform alerts, the admin system page and incidents."""

    platform_ops: PlatformOpsOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    check_platform_alerts_pipeline = orchestrator_pipeline(
        platform_ops.check_platform_alerts_orchestrator
    )
    send_platform_alert_pipeline = orchestrator_pipeline(
        platform_ops.send_platform_alert_orchestrator
    )
    get_admin_system_pipeline = orchestrator_pipeline(
        platform_ops.get_admin_system_orchestrator
    )
    record_maintenance_run_pipeline = orchestrator_pipeline(
        platform_ops.record_maintenance_run_orchestrator
    )
    create_incident_pipeline = orchestrator_pipeline(
        platform_ops.create_incident_orchestrator
    )
    list_incidents_pipeline = orchestrator_pipeline(
        platform_ops.list_incidents_orchestrator
    )
    check_channel_credentials_pipeline = orchestrator_pipeline(
        platform_ops.check_channel_credentials_orchestrator
    )
