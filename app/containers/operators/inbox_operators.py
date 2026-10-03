from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.inbox_pipelines import InboxPipelinesContainer
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class InboxOperatorsContainer(containers.DeclarativeContainer):
    """Operators of the team inbox, each in its business's scope."""

    inbox_pipelines: InboxPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    list_inbox_operator = pipeline_operator(
        inbox_pipelines.list_inbox_pipeline, storage_scope
    )
    count_inbox_views_operator = pipeline_operator(
        inbox_pipelines.count_inbox_views_pipeline, storage_scope
    )
    list_inbox_assignees_operator = pipeline_operator(
        inbox_pipelines.list_inbox_assignees_pipeline, storage_scope
    )
    assign_conversation_operator = pipeline_operator(
        inbox_pipelines.assign_conversation_pipeline, storage_scope
    )
    get_inbox_settings_operator = pipeline_operator(
        inbox_pipelines.get_inbox_settings_pipeline, storage_scope
    )
    update_inbox_settings_operator = pipeline_operator(
        inbox_pipelines.update_inbox_settings_pipeline, storage_scope
    )
    create_conversation_note_operator = pipeline_operator(
        inbox_pipelines.create_conversation_note_pipeline, storage_scope
    )
    list_conversation_notes_operator = pipeline_operator(
        inbox_pipelines.list_conversation_notes_pipeline, storage_scope
    )
    delete_conversation_note_operator = pipeline_operator(
        inbox_pipelines.delete_conversation_note_pipeline, storage_scope
    )
    list_quick_replies_operator = pipeline_operator(
        inbox_pipelines.list_quick_replies_pipeline, storage_scope
    )
    save_quick_reply_operator = pipeline_operator(
        inbox_pipelines.save_quick_reply_pipeline, storage_scope
    )
    delete_quick_reply_operator = pipeline_operator(
        inbox_pipelines.delete_quick_reply_pipeline, storage_scope
    )
    fill_quick_replies_operator = pipeline_operator(
        inbox_pipelines.fill_quick_replies_pipeline, storage_scope
    )
