from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.inbox_use_cases import InboxUseCasesContainer


class InboxOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of the team inbox (one use case each)."""

    inbox_use_cases: InboxUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    list_inbox_orchestrator = use_case_orchestrator(inbox_use_cases.list_inbox_use_case)
    count_inbox_views_orchestrator = use_case_orchestrator(
        inbox_use_cases.count_inbox_views_use_case
    )
    list_inbox_assignees_orchestrator = use_case_orchestrator(
        inbox_use_cases.list_inbox_assignees_use_case
    )
    assign_conversation_orchestrator = use_case_orchestrator(
        inbox_use_cases.assign_conversation_use_case
    )
    get_inbox_settings_orchestrator = use_case_orchestrator(
        inbox_use_cases.get_inbox_settings_use_case
    )
    update_inbox_settings_orchestrator = use_case_orchestrator(
        inbox_use_cases.update_inbox_settings_use_case
    )
    create_conversation_note_orchestrator = use_case_orchestrator(
        inbox_use_cases.create_conversation_note_use_case
    )
    list_conversation_notes_orchestrator = use_case_orchestrator(
        inbox_use_cases.list_conversation_notes_use_case
    )
    delete_conversation_note_orchestrator = use_case_orchestrator(
        inbox_use_cases.delete_conversation_note_use_case
    )
    list_quick_replies_orchestrator = use_case_orchestrator(
        inbox_use_cases.list_quick_replies_use_case
    )
    save_quick_reply_orchestrator = use_case_orchestrator(
        inbox_use_cases.save_quick_reply_use_case
    )
    delete_quick_reply_orchestrator = use_case_orchestrator(
        inbox_use_cases.delete_quick_reply_use_case
    )
    fill_quick_replies_orchestrator = use_case_orchestrator(
        inbox_use_cases.fill_quick_replies_use_case
    )
