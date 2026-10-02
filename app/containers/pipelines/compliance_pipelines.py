from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.compliance_orchestrators import (
    ComplianceOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class CompliancePipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines of the DPA, the audit log, contacts and their data rights,
    the retention purge job.
    """

    compliance_orchestrators: ComplianceOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Retention purge as a periodic job.
    purge_expired_recordings_pipeline = orchestrator_pipeline(
        compliance_orchestrators.purge_expired_recordings_job_orchestrator
    )

    # --- Compliance.
    get_dpa_status_pipeline = orchestrator_pipeline(
        compliance_orchestrators.get_dpa_status_orchestrator
    )
    accept_dpa_pipeline = orchestrator_pipeline(
        compliance_orchestrators.accept_dpa_orchestrator
    )
    list_audit_log_pipeline = orchestrator_pipeline(
        compliance_orchestrators.list_audit_log_orchestrator
    )
    export_contact_data_pipeline = orchestrator_pipeline(
        compliance_orchestrators.export_contact_data_orchestrator
    )
    delete_contact_data_pipeline = orchestrator_pipeline(
        compliance_orchestrators.delete_contact_data_orchestrator
    )
    get_dpa_document_pipeline = orchestrator_pipeline(
        compliance_orchestrators.get_dpa_document_orchestrator
    )
    list_contacts_pipeline = orchestrator_pipeline(
        compliance_orchestrators.list_contacts_orchestrator
    )
    get_contact_pipeline = orchestrator_pipeline(
        compliance_orchestrators.get_contact_orchestrator
    )
