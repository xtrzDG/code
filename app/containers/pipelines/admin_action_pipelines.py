from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.admin_action_orchestrators import (
    AdminActionOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class AdminActionPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the admin that acts."""

    admin_actions: AdminActionOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    extend_trial_pipeline = orchestrator_pipeline(
        admin_actions.extend_trial_orchestrator
    )
    give_discount_pipeline = orchestrator_pipeline(
        admin_actions.give_discount_orchestrator
    )
    grant_credit_pipeline = orchestrator_pipeline(
        admin_actions.grant_credit_orchestrator
    )
    waive_setup_fee_pipeline = orchestrator_pipeline(
        admin_actions.waive_setup_fee_orchestrator
    )
    mark_invoice_paid_pipeline = orchestrator_pipeline(
        admin_actions.mark_invoice_paid_orchestrator
    )
    override_plan_pipeline = orchestrator_pipeline(
        admin_actions.override_plan_orchestrator
    )
    complete_onboarding_pipeline = orchestrator_pipeline(
        admin_actions.complete_onboarding_orchestrator
    )
    list_client_notes_pipeline = orchestrator_pipeline(
        admin_actions.list_client_notes_orchestrator
    )
    create_client_note_pipeline = orchestrator_pipeline(
        admin_actions.create_client_note_orchestrator
    )
    update_client_note_pipeline = orchestrator_pipeline(
        admin_actions.update_client_note_orchestrator
    )
    delete_client_note_pipeline = orchestrator_pipeline(
        admin_actions.delete_client_note_orchestrator
    )
    get_client_timeline_pipeline = orchestrator_pipeline(
        admin_actions.get_client_timeline_orchestrator
    )
    send_critical_clients_digest_pipeline = orchestrator_pipeline(
        admin_actions.send_critical_clients_digest_orchestrator
    )
