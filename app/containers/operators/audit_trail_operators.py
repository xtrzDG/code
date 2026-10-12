from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.audit_trail_pipelines import (
    AuditTrailPipelinesContainer,
)
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class AuditTrailOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the audit log's hash chains. The owner's view runs in the
    business's scope. The admin views and the daily check name no business:
    they run unscoped, which reaches platform collections only, and the
    audit log, its chains' checks and checkpoints and the businesses are
    all platform collections.
    """

    audit_trail_pipelines: AuditTrailPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    get_audit_chain_status_operator = pipeline_operator(
        audit_trail_pipelines.get_audit_chain_status_pipeline, storage_scope
    )
    get_audit_chain_overview_operator = pipeline_operator(
        audit_trail_pipelines.get_audit_chain_overview_pipeline, storage_scope
    )
    list_platform_audit_log_operator = pipeline_operator(
        audit_trail_pipelines.list_platform_audit_log_pipeline, storage_scope
    )
    verify_audit_chains_operator = pipeline_operator(
        audit_trail_pipelines.verify_audit_chains_pipeline, storage_scope
    )
