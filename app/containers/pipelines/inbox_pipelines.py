from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.inbox_orchestrators import (
    InboxOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class InboxPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the team inbox."""

    inbox: InboxOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    list_inbox_pipeline = orchestrator_pipeline(inbox.list_inbox_orchestrator)
    count_inbox_views_pipeline = orchestrator_pipeline(
        inbox.count_inbox_views_orchestrator
    )
    list_inbox_assignees_pipeline = orchestrator_pipeline(
        inbox.list_inbox_assignees_orchestrator
    )
    assign_conversation_pipeline = orchestrator_pipeline(
        inbox.assign_conversation_orchestrator
    )
    get_inbox_settings_pipeline = orchestrator_pipeline(
        inbox.get_inbox_settings_orchestrator
    )
    update_inbox_settings_pipeline = orchestrator_pipeline(
        inbox.update_inbox_settings_orchestrator
    )
    create_conversation_note_pipeline = orchestrator_pipeline(
        inbox.create_conversation_note_orchestrator
    )
    list_conversation_notes_pipeline = orchestrator_pipeline(
        inbox.list_conversation_notes_orchestrator
    )
    delete_conversation_note_pipeline = orchestrator_pipeline(
        inbox.delete_conversation_note_orchestrator
    )
    list_quick_replies_pipeline = orchestrator_pipeline(
        inbox.list_quick_replies_orchestrator
    )
    save_quick_reply_pipeline = orchestrator_pipeline(
        inbox.save_quick_reply_orchestrator
    )
    delete_quick_reply_pipeline = orchestrator_pipeline(
        inbox.delete_quick_reply_orchestrator
    )
    fill_quick_replies_pipeline = orchestrator_pipeline(
        inbox.fill_quick_replies_orchestrator
    )
