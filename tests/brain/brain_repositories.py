"""Every repository a brain test world uses, over in-memory collections."""

from dataclasses import dataclass

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.assistant_repositories import AssistantVersionRepository
from app.repositories.billing_repositories import UsageEventRepository
from app.repositories.booking_repositories import HandoffRepository
from app.repositories.business_repositories import (
    BusinessProfileRepository,
    BusinessRepository,
    ChannelRepository,
)
from app.repositories.call_repository import CallRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.conversation_repositories import (
    ContactRepository,
    ConversationRepository,
    LlmTurnRepository,
    MessageRepository,
)
from app.repositories.feedback_repositories import FeedbackRequestRepository
from app.repositories.knowledge_repositories import (
    KnowledgeItemRepository,
    ScheduleExceptionRepository,
)
from app.repositories.privacy_repositories import SuppressionEntryRepository
from app.repositories.user_repositories import UserRepository
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.domain.feedback import FeedbackRequestDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.domain.suppression import SuppressionEntryDocument
from app.schemas.domain.users import UserDocument
from tests.brain.brain_memory import BrainMemory, build_brain_memory


@dataclass(frozen=True)
class BrainRepositories:
    business_repo: BusinessRepository
    profile_repo: BusinessProfileRepository
    exception_repo: ScheduleExceptionRepository
    version_repo: AssistantVersionRepository
    contact_repo: ContactRepository
    conversation_repo: ConversationRepository
    message_repo: MessageRepository
    llm_turn_repo: LlmTurnRepository
    usage_event_repo: UsageEventRepository
    channel_repo: ChannelRepository
    call_repo: CallRepository
    handoff_repo: HandoffRepository
    audit_log_repo: AuditLogRepository
    user_repo: UserRepository
    knowledge_item_repo: KnowledgeItemRepository
    feedback_request_repo: FeedbackRequestRepository
    suppression_entry_repo: SuppressionEntryRepository
    memory: BrainMemory


def build_brain_repositories() -> BrainRepositories:
    return BrainRepositories(
        business_repo=BusinessRepository(
            InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
        ),
        profile_repo=BusinessProfileRepository(
            InMemoryDocumentCollectionAdapter[BusinessProfileDocument](
                BusinessProfileDocument
            )
        ),
        exception_repo=ScheduleExceptionRepository(
            InMemoryDocumentCollectionAdapter[ScheduleExceptionDocument](
                ScheduleExceptionDocument
            )
        ),
        version_repo=AssistantVersionRepository(
            InMemoryDocumentCollectionAdapter[AssistantVersionDocument](
                AssistantVersionDocument
            )
        ),
        contact_repo=ContactRepository(
            InMemoryDocumentCollectionAdapter[ContactDocument](ContactDocument)
        ),
        conversation_repo=ConversationRepository(
            InMemoryDocumentCollectionAdapter[ConversationDocument](
                ConversationDocument
            )
        ),
        message_repo=MessageRepository(
            InMemoryDocumentCollectionAdapter[MessageDocument](MessageDocument)
        ),
        llm_turn_repo=LlmTurnRepository(
            InMemoryDocumentCollectionAdapter[LlmTurnDocument](LlmTurnDocument)
        ),
        usage_event_repo=UsageEventRepository(
            InMemoryDocumentCollectionAdapter[UsageEventDocument](UsageEventDocument)
        ),
        channel_repo=ChannelRepository(
            InMemoryDocumentCollectionAdapter(ChannelDocument)
        ),
        call_repo=CallRepository(InMemoryDocumentCollectionAdapter(CallDocument)),
        handoff_repo=HandoffRepository(
            InMemoryDocumentCollectionAdapter[HandoffDocument](HandoffDocument)
        ),
        audit_log_repo=AuditLogRepository(
            InMemoryDocumentCollectionAdapter[AuditLogEntryDocument](
                AuditLogEntryDocument
            )
        ),
        user_repo=UserRepository(
            InMemoryDocumentCollectionAdapter[UserDocument](UserDocument)
        ),
        knowledge_item_repo=KnowledgeItemRepository(
            InMemoryDocumentCollectionAdapter[KnowledgeItemDocument](
                KnowledgeItemDocument
            )
        ),
        feedback_request_repo=FeedbackRequestRepository(
            InMemoryDocumentCollectionAdapter(FeedbackRequestDocument)
        ),
        suppression_entry_repo=SuppressionEntryRepository(
            InMemoryDocumentCollectionAdapter(SuppressionEntryDocument)
        ),
        memory=build_brain_memory(),
    )
