"""The brain's cabinet routes on a small FastAPI app, wired like production."""

from dataclasses import dataclass, field

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.brain import MenuExtractionAdapterContract
from app.contracts.facilitators import ChannelMessageSenderFacilitatorContract
from app.contracts.operator_contract import OperatorContract
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.gateways.http.conversation_routes import build_conversation_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.menu_import_routes import build_menu_import_router
from app.gateways.http.user_authentication import build_current_user_dependency
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.conversations.owner_test_chat_orchestrator import (
    OwnerTestChatOrchestrator,
)
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.conversations.owner_test_chat_pipeline import OwnerTestChatPipeline
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.repositories.booking_repositories import BookingRepository, LeadRepository
from app.repositories.knowledge_repositories import ResourceRepository
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.call_recordings import CallRecordingQuery, RecordingAudio
from app.schemas.dto.conversation_feed import (
    ConversationDetailView,
    ConversationListQuery,
    ConversationPage,
    ConversationQuery,
    ConversationSummaryView,
    OwnerTestChatCommand,
    RateConversationCommand,
    SendStaffMessageCommand,
    StaffMessageResult,
)
from app.schemas.dto.conversations import AssistantReply
from app.schemas.dto.menu_import import (
    ConfirmImportedItemsCommand,
    ConfirmImportedItemsResult,
    DiscardedImportBatch,
    DiscardImportBatchCommand,
    ImportMenuCommand,
    MenuImportResult,
)
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ExternalServiceError,
    WhatsAppTemplateRejectedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.conversations.constrained_strings import RecordingMediaType
from app.schemas.typings.conversations.strings import (
    ChannelUserId,
    MessageText,
    RecordingStoragePath,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken
from app.transformers.conversations.call_view_transformer import CallViewTransformer
from app.transformers.conversations.conversation_summary_transformer import (
    ConversationSummaryTransformer,
)
from app.transformers.conversations.message_view_transformer import (
    MessageViewTransformer,
)
from app.use_cases.conversations.get_call_recording_use_case import (
    GetCallRecordingUseCase,
)
from app.use_cases.conversations.get_conversation_use_case import (
    GetConversationUseCase,
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
from tests.brain.brain_world import BrainWorld


class TokenAuthenticationOperator(OperatorContract[AccessToken, UserId]):
    """Bearer token -> user, from a fixed table."""

    def __init__(self, users_by_token: dict[str, UserId]) -> None:
        self._users_by_token: dict[str, UserId] = users_by_token

    def operate(self, input_data: AccessToken) -> UserId:
        user_id: UserId | None = self._users_by_token.get(str(input_data))
        if user_id is None:
            raise AuthenticationRequiredError("Unknown token.")

        return user_id


class RecordingChannelSender(ChannelMessageSenderFacilitatorContract):
    """Records messages to customers; `failure` makes the channel fail."""

    def __init__(self) -> None:
        self.sent: list[tuple[ChannelKind, str, str]] = []
        self.templates: list[tuple[str, str, str, list[str]]] = []
        self.failure: str | None = None
        self.template_rejection: str | None = None

    def send(
        self,
        business_id: BusinessId,
        channel: ChannelKind,
        channel_user_id: ChannelUserId,
        text: MessageText,
    ) -> None:
        if self.failure is not None:
            raise ExternalServiceError(self.failure)

        self.sent.append((channel, str(channel_user_id), str(text)))

    def send_whatsapp_template(
        self,
        business_id: BusinessId,
        channel_user_id: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language: LanguageTag,
        body_parameters: list[MessageText],
    ) -> None:
        raise AssertionError("Staff templates are sent in their own language.")

    def send_whatsapp_template_in_language(
        self,
        business_id: BusinessId,
        channel_user_id: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language_code: WhatsAppTemplateLanguageCode,
        body_parameters: list[MessageText],
    ) -> None:
        if self.failure is not None:
            raise ExternalServiceError(self.failure)

        if self.template_rejection is not None:
            raise WhatsAppTemplateRejectedError(self.template_rejection)

        self.templates.append(
            (
                str(channel_user_id),
                str(template_name),
                str(language_code),
                [str(parameter) for parameter in body_parameters],
            )
        )


class InMemoryRecordingStorage(RecordingStorageAdapterContract):
    """Recordings by path; `failure` makes the storage unreachable."""

    def __init__(self) -> None:
        self.recordings: dict[str, bytes] = {}
        self.reads: list[str] = []
        self.failure: str | None = None

    def read(self, recording_path: RecordingStoragePath) -> RecordingAudio | None:
        self.reads.append(str(recording_path))
        if self.failure is not None:
            raise ExternalServiceError(self.failure)

        content: bytes | None = self.recordings.get(str(recording_path))
        if content is None:
            return None

        return RecordingAudio(
            content=content, media_type=RecordingMediaType("audio/mpeg")
        )

    def delete(self, recording_path: RecordingStoragePath) -> None:
        self.recordings.pop(str(recording_path), None)


@dataclass
class CabinetStorage:
    """What the cabinet reads beside the brain world: bookings, leads, places."""

    booking_repo: BookingRepository = field(
        default_factory=lambda: BookingRepository(
            InMemoryDocumentCollectionAdapter(BookingDocument)
        )
    )
    lead_repo: LeadRepository = field(
        default_factory=lambda: LeadRepository(
            InMemoryDocumentCollectionAdapter(LeadDocument)
        )
    )
    resource_repo: ResourceRepository = field(
        default_factory=lambda: ResourceRepository(
            InMemoryDocumentCollectionAdapter(ResourceDocument)
        )
    )
    channel_sender: RecordingChannelSender = field(
        default_factory=RecordingChannelSender
    )
    recording_storage: InMemoryRecordingStorage = field(
        default_factory=InMemoryRecordingStorage
    )


@dataclass(frozen=True)
class CabinetOperators:
    list_conversations: OperatorContract[ConversationListQuery, ConversationPage]
    get_conversation: OperatorContract[ConversationQuery, ConversationDetailView]
    rate_conversation: OperatorContract[
        RateConversationCommand, ConversationSummaryView
    ]
    owner_test_chat: OperatorContract[OwnerTestChatCommand, AssistantReply]
    send_staff_message: OperatorContract[SendStaffMessageCommand, StaffMessageResult]
    get_call_recording: OperatorContract[CallRecordingQuery, RecordingAudio]
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
                prepare_test_message=OwnerTestChatOrchestrator(
                    authorize_business_access=world.authorize,
                    resolve_test_chat_version=ResolveTestChatVersionUseCase(
                        world.version_repo
                    ),
                ),
                turn_orchestrator=world.orchestrator,
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


def build_cabinet_client(
    world: BrainWorld,
    menu_extractor: MenuExtractionAdapterContract,
    users_by_token: dict[str, UserId],
    storage: CabinetStorage | None = None,
) -> TestClient:
    operators: CabinetOperators = build_cabinet_operators(
        world, menu_extractor, storage or CabinetStorage()
    )
    current_user = build_current_user_dependency(
        TokenAuthenticationOperator(users_by_token)
    )
    http_application = FastAPI()
    install_error_handlers(http_application)
    http_application.include_router(
        build_conversation_router(
            list_conversations_operator=operators.list_conversations,
            get_conversation_operator=operators.get_conversation,
            owner_test_chat_operator=operators.owner_test_chat,
            rate_conversation_operator=operators.rate_conversation,
            current_user=current_user,
            send_staff_message_operator=operators.send_staff_message,
            get_call_recording_operator=operators.get_call_recording,
        )
    )
    http_application.include_router(
        build_menu_import_router(
            import_menu_operator=operators.import_menu,
            confirm_imported_items_operator=operators.confirm_imported_items,
            discard_import_batch_operator=operators.discard_import_batch,
            current_user=current_user,
        )
    )
    return TestClient(http_application)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
