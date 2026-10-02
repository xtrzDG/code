from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory, Singleton

from app.containers.orchestrators.conversation_orchestrators import (
    ConversationOrchestratorsContainer,
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

    # --- Customer messages of every channel, one turn per customer at a time
    # across every API instance and worker (the customer's lock).
    customer_message_pipeline: Singleton[CustomerMessagePipelineContract] = Singleton(
        CustomerMessagePipeline,
        turn_orchestrator=conversation_orchestrators.conversation_turn_orchestrator,
        customer_locks=registries.customer_message_lock_registry,
    )

    # --- The owner's test chat.
    owner_test_chat_pipeline: Factory[
        PipelineContract[OwnerTestChatCommand, AssistantReply]
    ] = Factory(
        OwnerTestChatPipeline,
        prepare_test_message=conversation_orchestrators.owner_test_chat_orchestrator,
        turn_orchestrator=conversation_orchestrators.conversation_turn_orchestrator,
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

    # --- Conversation feed.
    list_conversations_pipeline = orchestrator_pipeline(
        conversation_orchestrators.list_conversations_orchestrator
    )
    get_conversation_pipeline = orchestrator_pipeline(
        conversation_orchestrators.get_conversation_orchestrator
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

    # --- Voice call start.
    start_voice_call_pipeline = orchestrator_pipeline(
        conversation_orchestrators.start_voice_call_orchestrator
    )
