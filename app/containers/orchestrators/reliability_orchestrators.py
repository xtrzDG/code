from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.platform_ops_use_cases import (
    PlatformOpsUseCasesContainer,
)
from app.containers.use_cases.reliability_use_cases import (
    ReliabilityUseCasesContainer,
)
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.reliability.record_incident_orchestrator import (
    RecordIncidentOrchestrator,
)
from app.schemas.dto.incidents import CreateIncidentCommand, IncidentView


class ReliabilityOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of the platform's reliability seen from the API."""

    reliability_use_cases: ReliabilityUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    platform_ops_use_cases: PlatformOpsUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    check_pipeline_health_orchestrator = use_case_orchestrator(
        reliability_use_cases.check_pipeline_health_use_case
    )
    watch_pipeline_orchestrator = use_case_orchestrator(
        reliability_use_cases.watch_pipeline_use_case
    )
    # POST /v1/admin/incidents: the incident, then its status announcement.
    record_incident_orchestrator: Factory[
        OrchestratorContract[CreateIncidentCommand, IncidentView]
    ] = Factory(
        RecordIncidentOrchestrator,
        create_incident=reliability_use_cases.create_incident_use_case,
        create_announcement=platform_ops_use_cases.create_announcement_use_case,
        link_announcement=reliability_use_cases.link_incident_announcement_use_case,
    )
    expand_incident_orchestrator = use_case_orchestrator(
        reliability_use_cases.expand_incident_use_case
    )
