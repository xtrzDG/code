from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import (
    ConversationDocument,
    ConversationMessageDocument,
    LlmTurnDocument,
)
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.domain.owners import (
    OtpChallengeDocument,
    OwnerDocument,
    OwnerSessionDocument,
)
from app.schemas.domain.questionnaires import QuestionnaireDocument


class AdaptersContainer(containers.DeclarativeContainer):
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]

    owner_collection: Singleton[InMemoryDocumentCollectionAdapter[OwnerDocument]] = (
        Singleton(
            InMemoryDocumentCollectionAdapter[OwnerDocument],
            document_type=OwnerDocument,
        )
    )
    otp_challenge_collection: Singleton[
        InMemoryDocumentCollectionAdapter[OtpChallengeDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[OtpChallengeDocument],
        document_type=OtpChallengeDocument,
    )
    owner_session_collection: Singleton[
        InMemoryDocumentCollectionAdapter[OwnerSessionDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[OwnerSessionDocument],
        document_type=OwnerSessionDocument,
    )
    business_collection: Singleton[
        InMemoryDocumentCollectionAdapter[BusinessDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[BusinessDocument],
        document_type=BusinessDocument,
    )
    questionnaire_collection: Singleton[
        InMemoryDocumentCollectionAdapter[QuestionnaireDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[QuestionnaireDocument],
        document_type=QuestionnaireDocument,
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
    conversation_collection: Singleton[
        InMemoryDocumentCollectionAdapter[ConversationDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[ConversationDocument],
        document_type=ConversationDocument,
    )
    conversation_message_collection: Singleton[
        InMemoryDocumentCollectionAdapter[ConversationMessageDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[ConversationMessageDocument],
        document_type=ConversationMessageDocument,
    )
    llm_turn_collection: Singleton[
        InMemoryDocumentCollectionAdapter[LlmTurnDocument]
    ] = Singleton(
        InMemoryDocumentCollectionAdapter[LlmTurnDocument],
        document_type=LlmTurnDocument,
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
