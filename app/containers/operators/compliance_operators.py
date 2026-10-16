from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.compliance_pipelines import CompliancePipelinesContainer
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class ComplianceOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the DPA, the audit log, contacts and their data rights,
    the retention purge job.
    """

    compliance_pipelines: CompliancePipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # Operators run inside the storage scope of the business they serve;
    # platform_pipeline_operator marks platform-level work (platform-wide).
    storage_scope = utilities.storage_scope

    # --- Retention purge as a periodic job.
    purge_expired_recordings_operator = platform_pipeline_operator(
        compliance_pipelines.purge_expired_recordings_pipeline, storage_scope
    )

    # --- Compliance.
    get_dpa_status_operator = pipeline_operator(
        compliance_pipelines.get_dpa_status_pipeline, storage_scope
    )
    accept_dpa_operator = pipeline_operator(
        compliance_pipelines.accept_dpa_pipeline, storage_scope
    )
    list_audit_log_operator = pipeline_operator(
        compliance_pipelines.list_audit_log_pipeline, storage_scope
    )
    export_contact_data_operator = pipeline_operator(
        compliance_pipelines.export_contact_data_pipeline, storage_scope
    )
    delete_contact_data_operator = pipeline_operator(
        compliance_pipelines.delete_contact_data_pipeline, storage_scope
    )
    get_dpa_document_operator = pipeline_operator(
        compliance_pipelines.get_dpa_document_pipeline, storage_scope
    )
    list_contacts_operator = pipeline_operator(
        compliance_pipelines.list_contacts_pipeline, storage_scope
    )
    get_contact_operator = pipeline_operator(
        compliance_pipelines.get_contact_pipeline, storage_scope
    )
