from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.compliance_use_cases import ComplianceUseCasesContainer
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.compliance.purge_expired_recordings_job_orchestrator import (
    PurgeExpiredRecordingsJobOrchestrator,
)
from app.schemas.dto.jobs import JobReport, JobTick


class ComplianceOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of the DPA, the audit log, contacts and their data
    rights, the retention purge job.
    """

    compliance_use_cases: ComplianceUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Retention purge as a periodic job.
    purge_expired_recordings_job_orchestrator: Factory[
        OrchestratorContract[JobTick, JobReport]
    ] = Factory(
        PurgeExpiredRecordingsJobOrchestrator,
        purge_expired_recordings=compliance_use_cases.purge_expired_recordings_use_case,
    )

    # --- Compliance.
    get_dpa_status_orchestrator = use_case_orchestrator(
        compliance_use_cases.get_dpa_status_use_case
    )
    accept_dpa_orchestrator = use_case_orchestrator(
        compliance_use_cases.accept_dpa_use_case
    )
    list_audit_log_orchestrator = use_case_orchestrator(
        compliance_use_cases.list_audit_log_use_case
    )
    export_contact_data_orchestrator = use_case_orchestrator(
        compliance_use_cases.export_contact_data_use_case
    )
    delete_contact_data_orchestrator = use_case_orchestrator(
        compliance_use_cases.delete_contact_data_use_case
    )
    get_dpa_document_orchestrator = use_case_orchestrator(
        compliance_use_cases.get_dpa_document_use_case
    )
    list_contacts_orchestrator = use_case_orchestrator(
        compliance_use_cases.list_contacts_use_case
    )
    get_contact_orchestrator = use_case_orchestrator(
        compliance_use_cases.get_contact_use_case
    )
