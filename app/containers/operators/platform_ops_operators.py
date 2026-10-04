from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.platform_ops_pipelines import (
    PlatformOpsPipelinesContainer,
)
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class PlatformOpsOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the platform's own operations. The alerts job and the
    system page count across every business, an incident names several
    (each gets its own owner notices and audit entry) and the backup runs
    belong to none, so those run platform-wide; sending an alert message
    reads no storage and runs in the worker's own (unscoped) scope.
    """

    platform_ops_pipelines: PlatformOpsPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    check_platform_alerts_operator = platform_pipeline_operator(
        platform_ops_pipelines.check_platform_alerts_pipeline, storage_scope
    )
    send_platform_alert_operator = pipeline_operator(
        platform_ops_pipelines.send_platform_alert_pipeline, storage_scope
    )
    get_admin_system_operator = platform_pipeline_operator(
        platform_ops_pipelines.get_admin_system_pipeline, storage_scope
    )
    record_maintenance_run_operator = platform_pipeline_operator(
        platform_ops_pipelines.record_maintenance_run_pipeline, storage_scope
    )
    create_incident_operator = platform_pipeline_operator(
        platform_ops_pipelines.create_incident_pipeline, storage_scope
    )
    list_incidents_operator = platform_pipeline_operator(
        platform_ops_pipelines.list_incidents_pipeline, storage_scope
    )
