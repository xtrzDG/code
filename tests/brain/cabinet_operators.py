"""The brain's cabinet operators, wired like production over a brain world."""

from dataclasses import dataclass

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.brain import MenuExtractionAdapterContract
from app.contracts.operator_contract import OperatorContract
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.conversations.owner_test_chat_orchestrator import (
    OwnerTestChatOrchestrator,
)
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.conversations.owner_test_chat_pipeline import OwnerTestChatPipeline
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.registries.turns.turn_slot_registry import build_test_chat_slots
from app.repositories.setup_repositories import ActivationEventRepository
from app.schemas.domain.setup import ActivationEventDocument
from app.schemas.dto.call_recordings import CallRecordingQuery, RecordingPart
from app.schemas.dto.conversation_feed.conversation_actions import (
    RateConversationCommand,
    SendStaffMessageCommand,
    StaffMessageResult,
)
from app.schemas.dto.conversation_feed.conversation_views import (
    ConversationDetailView,
    ConversationListQuery,
    ConversationMessagesQuery,
    ConversationPage,
    ConversationQuery,
    ConversationSummaryView,
    MessagePage,
)
from app.schemas.dto.conversation_feed.owner_test_chat import OwnerTestChatCommand
from app.schemas.dto.conversations import AssistantReply
from app.schemas.dto.media import MessageMediaQuery, StoredMediaFile
from app.schemas.dto.menu_import import (
    ConfirmImportedItemsCommand,
    ConfirmImportedItemsResult,
    DiscardedImportBatch,
    DiscardImportBatchCommand,
    ImportMenuCommand,
    MenuImportResult,
)
from app.transformers.conversations.call_view_transformer import CallViewTransformer
from app.transformers.conversations.conversation_summary_transformer import (
    ConversationSummaryTransformer,
)
from app.transformers.conversations.message_view_transformer import (
    MessageViewTransformer,
)
from app.use_cases.conversations.card.list_conversation_messages_use_case import (
    ListConversationMessagesUseCase,
)
from app.use_cases.conversations.get_call_recording_use_case import (
    GetCallRecordingUseCase,
)
from app.use_cases.conversations.get_conversation_use_case import GetConversationUseCase
from app.use_cases.conversations.get_message_media_use_case import (
    GetMessageMediaUseCase,
)
from app.use_cases.conversations.list_conversations_use_case import (
    ListConversationsUseCase,
)
from app.use_cases.conversations.rate_conversation_use_case import (
    RateConversationUseCase,
)
from app.use_cases.conversations.resolve_test_chat_version_use_case import (
    ResolveTestChatVersionUseCase,
)
from app.use_cases.conversations.send_staff_message_use_case import (
    SendStaffMessageUseCase,
)
from app.use_cases.menu_import.confirm_imported_items_use_case import (
    ConfirmImportedItemsUseCase,
)
from app.use_cases.menu_import.discard_import_batch_use_case import (
    DiscardImportBatchUseCase,
)
from app.use_cases.menu_import.import_menu_use_case import ImportMenuUseCase
from app.use_cases.setup.record_activation_event_use_case import (
    RecordActivationEventUseCase,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.analytics.recording_product_events import RecordingProductEvents
from tests.brain.brain_world import BrainWorld
from tests.brain.cabinet_fakes import CabinetStorage, KeepTestChatVersions
from tests.live_events.recording_event_publisher import RecordingEventPublisher


@dataclass(frozen=True)
class CabinetOperators:
    list_conversations: OperatorContract[ConversationListQuery, ConversationPage]
    get_conversation: OperatorContract[ConversationQuery, ConversationDetailView]
    rate_conversation: OperatorContract[
        RateConversationCommand, ConversationSummaryView
    ]
    owner_test_chat: OperatorContract[OwnerTestChatCommand, AssistantReply]
    send_staff_message: OperatorContract[SendStaffMessageCommand, StaffMessageResult]
    get_call_recording: OperatorContract[CallRecordingQuery, RecordingPart]
    get_message_media: OperatorContract[MessageMediaQuery, StoredMediaFile]
    list_conversation_messages: OperatorContract[ConversationMessagesQuery, MessagePage]
    import_menu: OperatorContract[ImportMenuCommand, MenuImportResult]
    confirm_imported_items: OperatorContract[
        ConfirmImportedItemsCommand, ConfirmImportedItemsResult
    ]
    discard_import_batch: OperatorContract[
        DiscardImportBatchCommand, DiscardedImportBatch
    ]


def build_cabinet_operators(
    world: BrainWorld,
    menu_extractor: MenuExtractionAdapterContract,
    storage: CabinetStorage,
) -> CabinetOperators:
    summary_transformer = ConversationSummaryTransformer()
    return CabinetOperators(
        list_conversations=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    ListConversationsUseCase(
                        authorize_business_access=world.authorize,
                        conversation_repo=world.conversation_repo,
                        contact_repo=world.contact_repo,
                        message_repo=world.message_repo,
                        summary_transformer=summary_transformer,
                        audit_log_repo=world.audit_log_repo,
                        wall_clock=world.clock.wall_clock(),
                    )
                )
            )
        ),
        get_conversation=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    GetConversationUseCase(
                        authorize_business_access=world.authorize,
                        conversation_repo=world.conversation_repo,
                        contact_repo=world.contact_repo,
                        message_repo=world.message_repo,
                        audit_log_repo=world.audit_log_repo,
                        summary_transformer=summary_transformer,
                        message_transformer=MessageViewTransformer(),
                        wall_clock=world.clock.wall_clock(),
                        call_repo=world.call_repo,
                        call_transformer=CallViewTransformer(),
                        booking_repo=storage.booking_repo,
                        lead_repo=storage.lead_repo,
                        handoff_repo=world.handoff_repo,
                        resource_repo=storage.resource_repo,
                        channel_repo=world.channel_repo,
                    )
                )
            )
        ),
        send_staff_message=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    SendStaffMessageUseCase(
                        authorize_business_access=world.authorize,
                        conversation_repo=world.conversation_repo,
                        message_repo=world.message_repo,
                        channel_repo=world.channel_repo,
                        audit_log_repo=world.audit_log_repo,
                        channel_message_sender=storage.channel_sender,
                        message_transformer=MessageViewTransformer(),
                        live_events=RecordingEventPublisher(),
                        wall_clock=world.clock.wall_clock(),
                    )
                )
            )
        ),
        list_conversation_messages=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    ListConversationMessagesUseCase(
                        authorize_business_access=world.authorize,
                        conversation_repo=world.conversation_repo,
                        message_repo=world.message_repo,
                        message_transformer=MessageViewTransformer(),
                        audit_log_repo=world.audit_log_repo,
                        wall_clock=world.clock.wall_clock(),
                    )
                )
            )
        ),
        get_call_recording=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    GetCallRecordingUseCase(
                        authorize_business_access=world.authorize,
                        call_repo=world.call_repo,
                        recording_storage=storage.recording_storage,
                        audit_log_repo=world.audit_log_repo,
                        wall_clock=world.clock.wall_clock(),
                    )
                )
            )
        ),
        get_message_media=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    GetMessageMediaUseCase(
                        authorize_business_access=world.authorize,
                        message_media_repo=storage.message_media_repo,
                        media_storage=storage.media_storage,
                        audit_log_repo=world.audit_log_repo,
                        wall_clock=world.clock.wall_clock(),
                    )
                )
            )
        ),
        rate_conversation=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    RateConversationUseCase(
                        authorize_business_access=world.authorize,
                        conversation_repo=world.conversation_repo,
                        contact_repo=world.contact_repo,
                        message_repo=world.message_repo,
                        summary_transformer=summary_transformer,
                        wall_clock=world.clock.wall_clock(),
                    )
                )
            )
        ),
        owner_test_chat=PipelineOperator(
            OwnerTestChatPipeline(
                # The brain's tests talk to versions they build themselves.
                prepare_test_chat_version=UseCaseOrchestrator(KeepTestChatVersions()),
                prepare_test_message=OwnerTestChatOrchestrator(
                    authorize_business_access=world.authorize,
                    resolve_test_chat_version=ResolveTestChatVersionUseCase(
                        world.version_repo
                    ),
                ),
                turn_orchestrator=world.orchestrator,
                record_activation_event=UseCaseOrchestrator(
                    RecordActivationEventUseCase(
                        ActivationEventRepository(
                            InMemoryDocumentCollectionAdapter(ActivationEventDocument)
                        ),
                        world.clock.wall_clock(),
                        product_events=RecordingProductEvents(),
                    )
                ),
                test_chat_slots=build_test_chat_slots(assemble_app_settings({})),
            )
        ),
        import_menu=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    ImportMenuUseCase(
                        authorize_business_access=world.authorize,
                        menu_extraction_adapter=menu_extractor,
                        knowledge_item_repo=world.knowledge_item_repo,
                        wall_clock=world.clock.wall_clock(),
                    )
                )
            )
        ),
        confirm_imported_items=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    ConfirmImportedItemsUseCase(
                        authorize_business_access=world.authorize,
                        knowledge_item_repo=world.knowledge_item_repo,
                        wall_clock=world.clock.wall_clock(),
                    )
                )
            )
        ),
        discard_import_batch=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    DiscardImportBatchUseCase(
                        authorize_business_access=world.authorize,
                        knowledge_item_repo=world.knowledge_item_repo,
                    )
                )
            )
        ),
    )
