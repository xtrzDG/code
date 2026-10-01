from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.schemas.domain.assistants import (
    AssistantVersionDocument,
    AutotestRunDocument,
)
from app.schemas.domain.billing import (
    InvoiceDocument,
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.domain.bookings import (
    BookingDocument,
    LeadDocument,
)
from app.schemas.domain.businesses import (
    BusinessDocument,
)
from app.schemas.domain.channels import (
    ChannelDocument,
)
from app.schemas.domain.compliance import (
    AuditLogEntryDocument,
    DpaAcceptanceDocument,
)
from app.schemas.domain.contacts import (
    ContactDocument,
)
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import (
    HandoffDocument,
    UnansweredQuestionDocument,
)
from app.schemas.domain.knowledge import (
    KnowledgeItemDocument,
)
from app.schemas.domain.profiles import (
    BusinessProfileDocument,
)
from app.schemas.domain.resources import (
    ResourceDocument,
    ScheduleExceptionDocument,
)
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)


class AdaptersContainer(containers.DeclarativeContainer):
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]

    user_collection: Singleton[InMemoryDocumentCollectionAdapter[UserDocument]] = (
        Singleton(
            InMemoryDocumentCollectionAdapter[UserDocument],
            document_type=UserDocument,
        )
    )
    otp_challenge_collection: Singleton[
        InMemoryDocumentCollectionAdapter[OtpChallengeDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[OtpChallengeDocument],
        document_type=OtpChallengeDocument,
    )
    user_session_collection: Singleton[
        InMemoryDocumentCollectionAdapter[UserSessionDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[UserSessionDocument],
        document_type=UserSessionDocument,
    )
    business_collection: Singleton[
        InMemoryDocumentCollectionAdapter[BusinessDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[BusinessDocument],
        document_type=BusinessDocument,
    )
    channel_collection: Singleton[
        InMemoryDocumentCollectionAdapter[ChannelDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[ChannelDocument],
        document_type=ChannelDocument,
    )
    business_profile_collection: Singleton[
        InMemoryDocumentCollectionAdapter[BusinessProfileDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[BusinessProfileDocument],
        document_type=BusinessProfileDocument,
    )
    knowledge_item_collection: Singleton[
        InMemoryDocumentCollectionAdapter[KnowledgeItemDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[KnowledgeItemDocument],
        document_type=KnowledgeItemDocument,
    )
    resource_collection: Singleton[
        InMemoryDocumentCollectionAdapter[ResourceDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[ResourceDocument],
        document_type=ResourceDocument,
    )
    schedule_exception_collection: Singleton[
        InMemoryDocumentCollectionAdapter[ScheduleExceptionDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[ScheduleExceptionDocument],
        document_type=ScheduleExceptionDocument,
    )
    contact_collection: Singleton[
        InMemoryDocumentCollectionAdapter[ContactDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[ContactDocument],
        document_type=ContactDocument,
    )
    conversation_collection: Singleton[
        InMemoryDocumentCollectionAdapter[ConversationDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[ConversationDocument],
        document_type=ConversationDocument,
    )
    message_collection: Singleton[
        InMemoryDocumentCollectionAdapter[MessageDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[MessageDocument],
        document_type=MessageDocument,
    )
    llm_turn_collection: Singleton[
        InMemoryDocumentCollectionAdapter[LlmTurnDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[LlmTurnDocument],
        document_type=LlmTurnDocument,
    )
    call_collection: Singleton[InMemoryDocumentCollectionAdapter[CallDocument]] = (
        Singleton(
            InMemoryDocumentCollectionAdapter[CallDocument],
            document_type=CallDocument,
        )
    )
    booking_collection: Singleton[
        InMemoryDocumentCollectionAdapter[BookingDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[BookingDocument],
        document_type=BookingDocument,
    )
    lead_collection: Singleton[InMemoryDocumentCollectionAdapter[LeadDocument]] = (
        Singleton(
            InMemoryDocumentCollectionAdapter[LeadDocument],
            document_type=LeadDocument,
        )
    )
    handoff_collection: Singleton[
        InMemoryDocumentCollectionAdapter[HandoffDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[HandoffDocument],
        document_type=HandoffDocument,
    )
    unanswered_question_collection: Singleton[
        InMemoryDocumentCollectionAdapter[UnansweredQuestionDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[UnansweredQuestionDocument],
        document_type=UnansweredQuestionDocument,
    )
    assistant_version_collection: Singleton[
        InMemoryDocumentCollectionAdapter[AssistantVersionDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[AssistantVersionDocument],
        document_type=AssistantVersionDocument,
    )
    autotest_run_collection: Singleton[
        InMemoryDocumentCollectionAdapter[AutotestRunDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[AutotestRunDocument],
        document_type=AutotestRunDocument,
    )
    subscription_collection: Singleton[
        InMemoryDocumentCollectionAdapter[SubscriptionDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[SubscriptionDocument],
        document_type=SubscriptionDocument,
    )
    invoice_collection: Singleton[
        InMemoryDocumentCollectionAdapter[InvoiceDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[InvoiceDocument],
        document_type=InvoiceDocument,
    )
    usage_event_collection: Singleton[
        InMemoryDocumentCollectionAdapter[UsageEventDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[UsageEventDocument],
        document_type=UsageEventDocument,
    )
    audit_log_entry_collection: Singleton[
        InMemoryDocumentCollectionAdapter[AuditLogEntryDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[AuditLogEntryDocument],
        document_type=AuditLogEntryDocument,
    )
    dpa_acceptance_collection: Singleton[
        InMemoryDocumentCollectionAdapter[DpaAcceptanceDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[DpaAcceptanceDocument],
        document_type=DpaAcceptanceDocument,
    )
