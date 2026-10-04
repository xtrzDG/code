from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory, Singleton

from app.containers.orchestrators.conversation_orchestrators import (
    ConversationOrchestratorsContainer,
)
from app.containers.orchestrators.setup_orchestrators import (
    SetupOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline
from app.containers.registries import RegistriesContainer
from app.contracts.conversation_flow import CustomerMessagePipelineContract
from app.contracts.pipeline_contract import PipelineContract
from app.pipelines.conversations.customer_message_pipeline import (
    CustomerMessagePipeline,
)
from app.pipelines.conversations.owner_test_chat_pipeline import (
    OwnerTestChatPipeline,
)
from app.schemas.dto.conversation_feed.owner_test_chat import OwnerTestChatCommand
from app.schemas.dto.conversations import AssistantReply


class ConversationPipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines of the conversation engine (one customer message, one
    voice tool call), the owner's test chat, the conversation feed and
    the voice webhooks.
    """

    conversation_orchestrators: ConversationOrchestratorsContainer = (
        DependenciesContainer()  # type: ignore[assignment]
    )
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    setup_orchestrators: SetupOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Customer messages of every channel, one turn per customer at a time
    # across every API instance and worker (the customer's lock).
    customer_message_pipeline: Singleton[CustomerMessagePipelineContract] = Singleton(
        CustomerMessagePipeline,
        turn_orchestrator=conversation_orchestrators.conversation_turn_orchestrator,
        customer_locks=registries.customer_message_lock_registry,
        turn_slots=registries.customer_turn_slots,
    )

    # --- The owner's test chat.
    owner_test_chat_pipeline: Factory[
        PipelineContract[OwnerTestChatCommand, AssistantReply]
    ] = Factory(
        OwnerTestChatPipeline,
        prepare_test_chat_version=setup_orchestrators.prepare_test_chat_version_orchestrator,
        prepare_test_message=conversation_orchestrators.owner_test_chat_orchestrator,
        turn_orchestrator=conversation_orchestrators.conversation_turn_orchestrator,
        record_activation_event=setup_orchestrators.record_activation_event_orchestrator,
        test_chat_slots=registries.test_chat_slots,
    )

    # --- Voice webhooks.
    voice_tool_webhook_pipeline = orchestrator_pipeline(
        conversation_orchestrators.voice_tool_webhook_orchestrator
    )
    post_call_webhook_pipeline = orchestrator_pipeline(
        conversation_orchestrators.accept_post_call_webhook_orchestrator
    )
    process_post_call_pipeline = orchestrator_pipeline(
        conversation_orchestrators.process_post_call_orchestrator
    )
    archive_call_recording_pipeline = orchestrator_pipeline(
        conversation_orchestrators.archive_call_recording_orchestrator
    )

    # --- Conversation feed.
    list_conversations_pipeline = orchestrator_pipeline(
        conversation_orchestrators.list_conversations_orchestrator
    )
    get_conversation_pipeline = orchestrator_pipeline(
        conversation_orchestrators.get_conversation_orchestrator
    )
    list_conversation_messages_pipeline = orchestrator_pipeline(
        conversation_orchestrators.list_conversation_messages_orchestrator
    )
    rate_conversation_pipeline = orchestrator_pipeline(
        conversation_orchestrators.rate_conversation_orchestrator
    )
    send_staff_message_pipeline = orchestrator_pipeline(
        conversation_orchestrators.send_staff_message_orchestrator
    )
    get_call_recording_pipeline = orchestrator_pipeline(
        conversation_orchestrators.get_call_recording_orchestrator
    )
    get_message_media_pipeline = orchestrator_pipeline(
        conversation_orchestrators.get_message_media_orchestrator
    )
    get_answer_correction_draft_pipeline = orchestrator_pipeline(
        conversation_orchestrators.get_answer_correction_draft_orchestrator
    )
    correct_answer_pipeline = orchestrator_pipeline(
        conversation_orchestrators.correct_answer_orchestrator
    )
    list_answers_to_improve_pipeline = orchestrator_pipeline(
        conversation_orchestrators.list_answers_to_improve_orchestrator
    )

    # --- Voice call start.
    start_voice_call_pipeline = orchestrator_pipeline(
        conversation_orchestrators.start_voice_call_orchestrator
    )
