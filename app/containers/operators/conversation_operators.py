from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.conversation_pipelines import (
    ConversationPipelinesContainer,
)
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class ConversationOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the owner's test chat, the conversation feed and the voice
    webhooks (customer messages arrive through the channel operators).
    """

    conversation_pipelines: ConversationPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # Operators run inside the storage scope of the business they serve;
    # platform_pipeline_operator marks platform-level work (platform-wide).
    storage_scope = utilities.storage_scope

    # --- The owner's test chat.
    owner_test_chat_operator = pipeline_operator(
        conversation_pipelines.owner_test_chat_pipeline, storage_scope
    )

    # --- Voice webhooks.
    voice_tool_webhook_operator = platform_pipeline_operator(
        conversation_pipelines.voice_tool_webhook_pipeline, storage_scope
    )
    post_call_webhook_operator = platform_pipeline_operator(
        conversation_pipelines.post_call_webhook_pipeline, storage_scope
    )
    process_post_call_operator = platform_pipeline_operator(
        conversation_pipelines.process_post_call_pipeline, storage_scope
    )
    # The archive job names its business: it runs in that business's scope.
    archive_call_recording_operator = pipeline_operator(
        conversation_pipelines.archive_call_recording_pipeline, storage_scope
    )

    # --- Conversation feed.
    list_conversations_operator = pipeline_operator(
        conversation_pipelines.list_conversations_pipeline, storage_scope
    )
    get_conversation_operator = pipeline_operator(
        conversation_pipelines.get_conversation_pipeline, storage_scope
    )
    list_conversation_messages_operator = pipeline_operator(
        conversation_pipelines.list_conversation_messages_pipeline, storage_scope
    )
    rate_conversation_operator = pipeline_operator(
        conversation_pipelines.rate_conversation_pipeline, storage_scope
    )
    send_staff_message_operator = pipeline_operator(
        conversation_pipelines.send_staff_message_pipeline, storage_scope
    )
    get_call_recording_operator = pipeline_operator(
        conversation_pipelines.get_call_recording_pipeline, storage_scope
    )
    get_message_media_operator = pipeline_operator(
        conversation_pipelines.get_message_media_pipeline, storage_scope
    )
    get_answer_correction_draft_operator = pipeline_operator(
        conversation_pipelines.get_answer_correction_draft_pipeline, storage_scope
    )
    correct_answer_operator = pipeline_operator(
        conversation_pipelines.correct_answer_pipeline, storage_scope
    )
    list_answers_to_improve_operator = pipeline_operator(
        conversation_pipelines.list_answers_to_improve_pipeline, storage_scope
    )

    # --- Voice call start.
    start_voice_call_operator = platform_pipeline_operator(
        conversation_pipelines.start_voice_call_pipeline, storage_scope
    )
