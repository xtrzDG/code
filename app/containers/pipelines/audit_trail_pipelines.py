from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.audit_trail_orchestrators import (
    AuditTrailOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class AuditTrailPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the audit log's hash chains."""

    audit_trail: AuditTrailOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    get_audit_chain_status_pipeline = orchestrator_pipeline(
        audit_trail.get_audit_chain_status_orchestrator
    )
    get_audit_chain_overview_pipeline = orchestrator_pipeline(
        audit_trail.get_audit_chain_overview_orchestrator
    )
    list_platform_audit_log_pipeline = orchestrator_pipeline(
        audit_trail.list_platform_audit_log_orchestrator
    )
    verify_audit_chains_pipeline = orchestrator_pipeline(
        audit_trail.verify_audit_chains_orchestrator
    )
