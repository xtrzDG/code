from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.platform_ops_use_cases import (
    PlatformOpsUseCasesContainer,
)


class PlatformOpsOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of the platform's own operations (one use case each): the
    platform alerts job and its messages, the admin system page and the
    incident log.
    """

    platform_ops_use_cases: PlatformOpsUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    check_platform_alerts_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.check_platform_alerts_use_case
    )
    send_platform_alert_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.send_platform_alert_use_case
    )
    get_admin_system_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.get_admin_system_use_case
    )
    record_maintenance_run_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.record_maintenance_run_use_case
    )
    create_incident_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.create_incident_use_case
    )
    list_incidents_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.list_incidents_use_case
    )
    check_channel_credentials_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.check_channel_credentials_use_case
    )
