from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.admin_action_pipelines import (
    AdminActionPipelinesContainer,
)
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class AdminActionOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the admin that acts. Each request names one client and
    runs in that client's storage scope; the daily digest reads the health
    changes and standings of every client, so it runs platform-wide.
    """

    admin_action_pipelines: AdminActionPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    extend_trial_operator = pipeline_operator(
        admin_action_pipelines.extend_trial_pipeline, storage_scope
    )
    give_discount_operator = pipeline_operator(
        admin_action_pipelines.give_discount_pipeline, storage_scope
    )
    grant_credit_operator = pipeline_operator(
        admin_action_pipelines.grant_credit_pipeline, storage_scope
    )
    waive_setup_fee_operator = pipeline_operator(
        admin_action_pipelines.waive_setup_fee_pipeline, storage_scope
    )
    mark_invoice_paid_operator = pipeline_operator(
        admin_action_pipelines.mark_invoice_paid_pipeline, storage_scope
    )
    override_plan_operator = pipeline_operator(
        admin_action_pipelines.override_plan_pipeline, storage_scope
    )
    complete_onboarding_operator = pipeline_operator(
        admin_action_pipelines.complete_onboarding_pipeline, storage_scope
    )
    list_client_notes_operator = pipeline_operator(
        admin_action_pipelines.list_client_notes_pipeline, storage_scope
    )
    create_client_note_operator = pipeline_operator(
        admin_action_pipelines.create_client_note_pipeline, storage_scope
    )
    update_client_note_operator = pipeline_operator(
        admin_action_pipelines.update_client_note_pipeline, storage_scope
    )
    delete_client_note_operator = pipeline_operator(
        admin_action_pipelines.delete_client_note_pipeline, storage_scope
    )
    get_client_timeline_operator = pipeline_operator(
        admin_action_pipelines.get_client_timeline_pipeline, storage_scope
    )
    send_critical_clients_digest_operator = platform_pipeline_operator(
        admin_action_pipelines.send_critical_clients_digest_pipeline, storage_scope
    )
