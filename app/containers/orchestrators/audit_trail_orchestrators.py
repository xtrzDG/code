from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.audit_trail_use_cases import (
    AuditTrailUseCasesContainer,
)


class AuditTrailOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of the audit log's hash chains."""

    audit_trail_use_cases: AuditTrailUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_audit_chain_status_orchestrator = use_case_orchestrator(
        audit_trail_use_cases.get_audit_chain_status_use_case
    )
    get_audit_chain_overview_orchestrator = use_case_orchestrator(
        audit_trail_use_cases.get_audit_chain_overview_use_case
    )
    list_platform_audit_log_orchestrator = use_case_orchestrator(
        audit_trail_use_cases.list_platform_audit_log_use_case
    )
    verify_audit_chains_orchestrator = use_case_orchestrator(
        audit_trail_use_cases.verify_audit_chains_use_case
    )
    purge_audit_log_orchestrator = use_case_orchestrator(
        audit_trail_use_cases.purge_audit_log_use_case
    )
