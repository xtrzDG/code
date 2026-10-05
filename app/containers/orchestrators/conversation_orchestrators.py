from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.orchestrators.call_orchestrators import (
    CallOrchestratorsContainer,
)
from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.call_use_cases import CallUseCasesContainer
from app.containers.use_cases.conversation_feed_use_cases import (
    ConversationFeedUseCasesContainer,
)
from app.containers.use_cases.conversation_use_cases import (
    ConversationUseCasesContainer,
)
from app.containers.use_cases.delivery_use_cases import DeliveryUseCasesContainer
from app.containers.use_cases.feedback_use_cases import FeedbackUseCasesContainer
from app.containers.use_cases.follow_up_use_cases import FollowUpUseCasesContainer
from app.containers.use_cases.spend_guard_use_cases import SpendGuardUseCasesContainer
from app.containers.use_cases.voice_use_cases import VoiceUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.conversation_flow import (
    ConversationTurnOrchestratorContract,
    VoiceToolCallOrchestratorContract,
)
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.channels.inbox.accept_post_call_webhook_orchestrator import (
    AcceptPostCallWebhookOrchestrator,
)
from app.orchestrators.channels.inbox.process_post_call_orchestrator import (
    ProcessPostCallOrchestrator,
)
from app.orchestrators.channels.post_call_follow_ups import PostCallFollowUps
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
from app.schemas.dto.jobs import JobReport, QueuedJobInput
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
    delivery_use_cases: DeliveryUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    call_use_cases: CallUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    call_orchestrators: CallOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]
    feedback_use_cases: FeedbackUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    spend_guard_use_cases: SpendGuardUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

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
            answer_customer_signal=feedback_use_cases.answer_customer_signal_use_case,
            check_spend=spend_guard_use_cases.check_business_spend_use_case,
        )
    )
    # Autotests play the same turns without the spend guard: a check must
    # test the version's own model, and runs have their own limits (one at
    # a time, 20 a day per business).
    autotest_turn_orchestrator: Factory[ConversationTurnOrchestratorContract] = Factory(
        ConversationTurnOrchestrator,
        prepare_turn=conversation_use_cases.prepare_conversation_turn_use_case,
        generate_reply=conversation_use_cases.generate_assistant_reply_use_case,
        handoff_to_human=follow_up_use_cases.handoff_to_human_use_case,
        record_reply=conversation_use_cases.record_assistant_reply_use_case,
        localized_text_resolver=utilities.localized_text_resolver,
        storage_scope=utilities.storage_scope,
        answer_customer_signal=feedback_use_cases.answer_customer_signal_use_case,
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
        admit_owner_action=spend_guard_use_cases.admit_owner_action_use_case,
    )

    # --- Voice webhooks.
    voice_tool_webhook_orchestrator: Factory[
        OrchestratorContract[VoiceToolWebhookRequest, VoiceToolCallResult]
    ] = Factory(
        VoiceToolWebhookOrchestrator,
        authenticate_voice_tool_call=voice_use_cases.authenticate_voice_tool_call_use_case,
        voice_tool_call=voice_tool_call_orchestrator,
    )
    # The webhook verifies the report and keeps it in the inbox; the worker
    # runs the post-call flow on it (the stored report is not verified
    # again: a retry may come after the signature's 30 minutes).
    accept_post_call_webhook_orchestrator: Factory[
        OrchestratorContract[PostCallWebhookRequest, PostCallWebhookOutcome]
    ] = Factory(
        AcceptPostCallWebhookOrchestrator,
        authenticate_post_call=voice_use_cases.authenticate_post_call_use_case,
        store_post_call_report=delivery_use_cases.store_post_call_report_use_case,
        read_failed_call_start=call_use_cases.read_failed_call_start_use_case,
        handle_missed_call=call_orchestrators.missed_call_orchestrator,
    )
    post_call_webhook_orchestrator: Factory[
        OrchestratorContract[PostCallWebhookRequest, PostCallWebhookOutcome]
    ] = Factory(
        PostCallWebhookOrchestrator,
        authenticate_post_call=delivery_use_cases.read_accepted_post_call_use_case,
        record_finished_call=voice_use_cases.record_finished_call_use_case,
        follow_ups=Factory(
            PostCallFollowUps,
            open_call_conversation=call_use_cases.open_call_conversation_use_case,
            audit_call_replies=voice_use_cases.audit_call_replies_use_case,
            find_missed_voice_call=call_use_cases.find_missed_voice_call_use_case,
            register_missed_call=call_use_cases.register_missed_call_use_case,
            summarize_call=call_use_cases.summarize_call_use_case,
            send_call_confirmation=voice_use_cases.send_call_confirmation_use_case,
            send_call_links=voice_use_cases.send_call_links_use_case,
            schedule_recording_archive=voice_use_cases.schedule_recording_archive_use_case,
        ),
    )
    archive_call_recording_orchestrator = use_case_orchestrator(
        voice_use_cases.archive_call_recording_use_case
    )
    process_post_call_orchestrator: Factory[
        OrchestratorContract[QueuedJobInput, JobReport]
    ] = Factory(
        ProcessPostCallOrchestrator,
        claim_inbound_event=delivery_use_cases.claim_inbound_event_use_case,
        process_finished_call=post_call_webhook_orchestrator,
        finish_inbound_event=delivery_use_cases.finish_inbound_event_use_case,
        release_inbound_event=delivery_use_cases.release_inbound_event_use_case,
    )

    # --- Conversation feed.
    list_conversations_orchestrator = use_case_orchestrator(
        conversation_feed_use_cases.list_conversations_use_case
    )
    get_conversation_orchestrator = use_case_orchestrator(
        conversation_feed_use_cases.get_conversation_use_case
    )
    get_conversation_quality_orchestrator = use_case_orchestrator(
        conversation_feed_use_cases.get_conversation_quality_use_case
    )
    list_conversation_messages_orchestrator = use_case_orchestrator(
        conversation_feed_use_cases.list_conversation_messages_use_case
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
    get_message_media_orchestrator = use_case_orchestrator(
        conversation_feed_use_cases.get_message_media_use_case
    )
    # Teaching the assistant: "Fix this answer", answers worth improving.
    get_answer_correction_draft_orchestrator = use_case_orchestrator(
        conversation_feed_use_cases.get_answer_correction_draft_use_case
    )
    correct_answer_orchestrator = use_case_orchestrator(
        conversation_feed_use_cases.correct_answer_use_case
    )
    list_answers_to_improve_orchestrator = use_case_orchestrator(
        conversation_feed_use_cases.list_answers_to_improve_use_case
    )

    # --- Voice call start.
    start_voice_call_orchestrator = use_case_orchestrator(
        voice_use_cases.start_voice_call_use_case
    )
