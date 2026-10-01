from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters import AdaptersContainer
from app.repositories.assistant_repositories import (
    AssistantVersionRepository,
    AutotestRunRepository,
)
from app.repositories.booking_repositories import BookingRepository, LeadRepository
from app.repositories.business_repositories import (
    BusinessRepository,
    QuestionnaireRepository,
)
from app.repositories.conversation_repositories import (
    ConversationMessageRepository,
    ConversationRepository,
    LlmTurnRepository,
)
from app.repositories.handoff_repositories import (
    HandoffRepository,
    UnansweredQuestionRepository,
)
from app.repositories.owner_repositories import (
    OtpChallengeRepository,
    OwnerRepository,
    OwnerSessionRepository,
)


class RepositoriesContainer(containers.DeclarativeContainer):
    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]

    owner_repo: Singleton[OwnerRepository] = Singleton(
        OwnerRepository,
        collection=adapters.owner_collection,
    )
    otp_challenge_repo: Singleton[OtpChallengeRepository] = Singleton(
        OtpChallengeRepository,
        collection=adapters.otp_challenge_collection,
    )
    owner_session_repo: Singleton[OwnerSessionRepository] = Singleton(
        OwnerSessionRepository,
        collection=adapters.owner_session_collection,
    )
    business_repo: Singleton[BusinessRepository] = Singleton(
        BusinessRepository,
        collection=adapters.business_collection,
    )
    questionnaire_repo: Singleton[QuestionnaireRepository] = Singleton(
        QuestionnaireRepository,
        collection=adapters.questionnaire_collection,
    )
    assistant_version_repo: Singleton[AssistantVersionRepository] = Singleton(
        AssistantVersionRepository,
        collection=adapters.assistant_version_collection,
    )
    autotest_run_repo: Singleton[AutotestRunRepository] = Singleton(
        AutotestRunRepository,
        collection=adapters.autotest_run_collection,
    )
    conversation_repo: Singleton[ConversationRepository] = Singleton(
        ConversationRepository,
        collection=adapters.conversation_collection,
    )
    conversation_message_repo: Singleton[ConversationMessageRepository] = Singleton(
        ConversationMessageRepository,
        collection=adapters.conversation_message_collection,
    )
    llm_turn_repo: Singleton[LlmTurnRepository] = Singleton(
        LlmTurnRepository,
        collection=adapters.llm_turn_collection,
    )
    booking_repo: Singleton[BookingRepository] = Singleton(
        BookingRepository,
        collection=adapters.booking_collection,
    )
    lead_repo: Singleton[LeadRepository] = Singleton(
        LeadRepository,
        collection=adapters.lead_collection,
    )
    handoff_repo: Singleton[HandoffRepository] = Singleton(
        HandoffRepository,
        collection=adapters.handoff_collection,
    )
    unanswered_question_repo: Singleton[UnansweredQuestionRepository] = Singleton(
        UnansweredQuestionRepository,
        collection=adapters.unanswered_question_collection,
    )
