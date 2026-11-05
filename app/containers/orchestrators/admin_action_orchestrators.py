from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.admin_action_use_cases import (
    AdminActionUseCasesContainer,
)


class AdminActionOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of the admin that acts (one use case each)."""

    admin_action_use_cases: AdminActionUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    extend_trial_orchestrator = use_case_orchestrator(
        admin_action_use_cases.extend_trial_use_case
    )
    give_discount_orchestrator = use_case_orchestrator(
        admin_action_use_cases.give_discount_use_case
    )
    grant_credit_orchestrator = use_case_orchestrator(
        admin_action_use_cases.grant_credit_use_case
    )
    waive_setup_fee_orchestrator = use_case_orchestrator(
        admin_action_use_cases.waive_setup_fee_use_case
    )
    mark_invoice_paid_orchestrator = use_case_orchestrator(
        admin_action_use_cases.mark_invoice_paid_use_case
    )
    override_plan_orchestrator = use_case_orchestrator(
        admin_action_use_cases.override_plan_use_case
    )
    complete_onboarding_orchestrator = use_case_orchestrator(
        admin_action_use_cases.complete_onboarding_use_case
    )
    list_client_notes_orchestrator = use_case_orchestrator(
        admin_action_use_cases.list_client_notes_use_case
    )
    create_client_note_orchestrator = use_case_orchestrator(
        admin_action_use_cases.create_client_note_use_case
    )
    update_client_note_orchestrator = use_case_orchestrator(
        admin_action_use_cases.update_client_note_use_case
    )
    delete_client_note_orchestrator = use_case_orchestrator(
        admin_action_use_cases.delete_client_note_use_case
    )
    get_client_timeline_orchestrator = use_case_orchestrator(
        admin_action_use_cases.get_client_timeline_use_case
    )
    send_critical_clients_digest_orchestrator = use_case_orchestrator(
        admin_action_use_cases.send_critical_clients_digest_use_case
    )
