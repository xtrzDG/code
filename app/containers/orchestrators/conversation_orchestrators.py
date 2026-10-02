from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.conversation_feed_use_cases import (
    ConversationFeedUseCasesContainer,
)
from app.containers.use_cases.conversation_use_cases import (
    ConversationUseCasesContainer,
)
from app.containers.use_cases.follow_up_use_cases import FollowUpUseCasesContainer
from app.containers.use_cases.voice_use_cases import VoiceUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.conversation_flow import (
    ConversationTurnOrchestratorContract,
    VoiceToolCallOrchestratorContract,
)
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.channels.post_call_webhook_orchestrator import (
    PostCallWebhookOrchestrator,
)
from app.orchestrators.channels.voice_tool_webhook_orchestrator import (
    VoiceToolWebhookOrchestrator,
)
from app.orchestrators.conversations.conversation_turn_orchestrator import (
    ConversationTurnOrchestrator,
)
from app.orchestrators.conversations.owner_test_chat_orchestrator import (
    OwnerTestChatOrchestrator,
)
from app.orchestrators.conversations.voice_tool_call_orchestrator import (
    VoiceToolCallOrchestrator,
)
from app.schemas.dto.conversation_feed.owner_test_chat import OwnerTestChatCommand
from app.schemas.dto.conversations import InboundMessage, VoiceToolCallResult
from app.schemas.dto.voice_webhooks import (
    PostCallWebhookOutcome,
    PostCallWebhookRequest,
    VoiceToolWebhookRequest,
)


class ConversationOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of the conversation engine (one customer message, one
    voice tool call), the owner's test chat, the conversation feed and
    the voice webhooks.
    """

    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    follow_up_use_cases: FollowUpUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    conversation_use_cases: ConversationUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    conversation_feed_use_cases: ConversationFeedUseCasesContainer = (
        DependenciesContainer()  # type: ignore[assignment]
    )
    voice_use_cases: VoiceUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Conversation engine: one customer message, one voice tool call.
    conversation_turn_orchestrator: Factory[ConversationTurnOrchestratorContract] = (
        Factory(
            ConversationTurnOrchestrator,
            prepare_turn=conversation_use_cases.prepare_conversation_turn_use_case,
            generate_reply=conversation_use_cases.generate_assistant_reply_use_case,
            handoff_to_human=follow_up_use_cases.handoff_to_human_use_case,
            record_reply=conversation_use_cases.record_assistant_reply_use_case,
            localized_text_resolver=utilities.localized_text_resolver,
            storage_scope=utilities.storage_scope,
        )
    )
    voice_tool_call_orchestrator: Factory[VoiceToolCallOrchestratorContract] = Factory(
        VoiceToolCallOrchestrator,
        open_voice_conversation=conversation_use_cases.open_voice_conversation_use_case,
        run_assistant_tool=conversation_use_cases.run_assistant_tool_use_case,
        record_voice_tool_call=conversation_use_cases.record_voice_tool_call_use_case,
        storage_scope=utilities.storage_scope,
    )
    owner_test_chat_orchestrator: Factory[
        OrchestratorContract[OwnerTestChatCommand, InboundMessage]
    ] = Factory(
        OwnerTestChatOrchestrator,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        resolve_test_chat_version=conversation_feed_use_cases.resolve_test_chat_version_use_case,
    )

    # --- Voice webhooks.
    voice_tool_webhook_orchestrator: Factory[
        OrchestratorContract[VoiceToolWebhookRequest, VoiceToolCallResult]
    ] = Factory(
        VoiceToolWebhookOrchestrator,
        authenticate_voice_tool_call=voice_use_cases.authenticate_voice_tool_call_use_case,
        voice_tool_call=voice_tool_call_orchestrator,
    )
    post_call_webhook_orchestrator: Factory[
        OrchestratorContract[PostCallWebhookRequest, PostCallWebhookOutcome]
    ] = Factory(
        PostCallWebhookOrchestrator,
        authenticate_post_call=voice_use_cases.authenticate_post_call_use_case,
        record_finished_call=voice_use_cases.record_finished_call_use_case,
        send_call_confirmation=voice_use_cases.send_call_confirmation_use_case,
    )

    # --- Conversation feed.
    list_conversations_orchestrator = use_case_orchestrator(
        conversation_feed_use_cases.list_conversations_use_case
    )
    get_conversation_orchestrator = use_case_orchestrator(
        conversation_feed_use_cases.get_conversation_use_case
    )
    rate_conversation_orchestrator = use_case_orchestrator(
        conversation_feed_use_cases.rate_conversation_use_case
    )
    send_staff_message_orchestrator = use_case_orchestrator(
        conversation_feed_use_cases.send_staff_message_use_case
    )
    get_call_recording_orchestrator = use_case_orchestrator(
        conversation_feed_use_cases.get_call_recording_use_case
    )

    # --- Voice call start.
    start_voice_call_orchestrator = use_case_orchestrator(
        voice_use_cases.start_voice_call_use_case
    )
