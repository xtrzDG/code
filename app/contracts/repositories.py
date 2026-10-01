"""Persistence contracts, one per document type.

Implementations must return independent copies: mutating a returned document
must not change stored state until `save` is called.
"""

from typing import Protocol

from app.contracts.repo_contract import RepoContract
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
from app.schemas.typings.accounts.constrained_strings import EmailAddress
from app.schemas.typings.accounts.prefixed_id import (
    OtpChallengeId,
    OwnerId,
    OwnerSessionId,
)
from app.schemas.typings.accounts.strings import AccessTokenHash
from app.schemas.typings.assistants.prefixed_id import (
    AssistantVersionId,
    AutotestRunId,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber


class OwnerRepoContract(RepoContract, Protocol):
    def save(self, owner: OwnerDocument) -> None:
        raise NotImplementedError

    def get(self, owner_id: OwnerId) -> OwnerDocument | None:
        raise NotImplementedError

    def find_by_phone_number(
        self,
        phone_number: E164PhoneNumber,
    ) -> OwnerDocument | None:
        raise NotImplementedError

    def find_by_email(self, email: EmailAddress) -> OwnerDocument | None:
        raise NotImplementedError


class OtpChallengeRepoContract(RepoContract, Protocol):
    def save(self, challenge: OtpChallengeDocument) -> None:
        raise NotImplementedError

    def get(self, challenge_id: OtpChallengeId) -> OtpChallengeDocument | None:
        raise NotImplementedError


class OwnerSessionRepoContract(RepoContract, Protocol):
    def save(self, session: OwnerSessionDocument) -> None:
        raise NotImplementedError

    def find_by_token_hash(
        self,
        token_hash: AccessTokenHash,
    ) -> OwnerSessionDocument | None:
        raise NotImplementedError

    def delete(self, session_id: OwnerSessionId) -> None:
        raise NotImplementedError


class BusinessRepoContract(RepoContract, Protocol):
    def save(self, business: BusinessDocument) -> None:
        raise NotImplementedError

    def get(self, business_id: BusinessId) -> BusinessDocument | None:
        raise NotImplementedError

    def list_by_owner(self, owner_id: OwnerId) -> list[BusinessDocument]:
        raise NotImplementedError


class QuestionnaireRepoContract(RepoContract, Protocol):
    def save(self, questionnaire: QuestionnaireDocument) -> None:
        raise NotImplementedError

    def get_by_business(
        self,
        business_id: BusinessId,
    ) -> QuestionnaireDocument | None:
        raise NotImplementedError


class AssistantVersionRepoContract(RepoContract, Protocol):
    def save(self, version: AssistantVersionDocument) -> None:
        raise NotImplementedError

    def get(self, version_id: AssistantVersionId) -> AssistantVersionDocument | None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[AssistantVersionDocument]:
        """Return versions ordered by version_number ascending."""
        raise NotImplementedError


class AutotestRunRepoContract(RepoContract, Protocol):
    def save(self, run: AutotestRunDocument) -> None:
        raise NotImplementedError

    def get(self, run_id: AutotestRunId) -> AutotestRunDocument | None:
        raise NotImplementedError


class ConversationRepoContract(RepoContract, Protocol):
    def save(self, conversation: ConversationDocument) -> None:
        raise NotImplementedError

    def get(self, conversation_id: ConversationId) -> ConversationDocument | None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[ConversationDocument]:
        """Return conversations ordered by last_message_at descending."""
        raise NotImplementedError


class ConversationMessageRepoContract(RepoContract, Protocol):
    def save(self, message: ConversationMessageDocument) -> None:
        raise NotImplementedError

    def list_by_conversation(
        self,
        conversation_id: ConversationId,
    ) -> list[ConversationMessageDocument]:
        """Return messages ordered by created_at ascending."""
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[ConversationMessageDocument]:
        raise NotImplementedError


class LlmTurnRepoContract(RepoContract, Protocol):
    def append(self, turn: LlmTurnDocument) -> None:
        """Store a new turn; turns are never updated or deleted."""
        raise NotImplementedError

    def list_by_conversation(
        self,
        conversation_id: ConversationId,
    ) -> list[LlmTurnDocument]:
        """Return turns ordered by sequence_number ascending."""
        raise NotImplementedError


class BookingRepoContract(RepoContract, Protocol):
    def save(self, booking: BookingDocument) -> None:
        raise NotImplementedError

    def get(self, booking_id: BookingId) -> BookingDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[BookingDocument]:
        """Return bookings ordered by starts_at ascending."""
        raise NotImplementedError


class LeadRepoContract(RepoContract, Protocol):
    def save(self, lead: LeadDocument) -> None:
        raise NotImplementedError

    def get(self, lead_id: LeadId) -> LeadDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[LeadDocument]:
        """Return leads ordered by created_at descending."""
        raise NotImplementedError


class HandoffRepoContract(RepoContract, Protocol):
    def save(self, handoff: HandoffDocument) -> None:
        raise NotImplementedError

    def get(self, handoff_id: HandoffId) -> HandoffDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[HandoffDocument]:
        """Return handoffs ordered by created_at descending."""
        raise NotImplementedError


class UnansweredQuestionRepoContract(RepoContract, Protocol):
    def save(self, question: UnansweredQuestionDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        question_id: UnansweredQuestionId,
    ) -> UnansweredQuestionDocument | None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[UnansweredQuestionDocument]:
        """Return questions ordered by occurrence_count descending."""
        raise NotImplementedError
