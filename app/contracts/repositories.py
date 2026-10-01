"""Persistence contracts, one per document type.

Implementations return independent copies: mutating a returned document does
not change stored state until it is saved. Every business-owned document is
looked up through its business id, so one tenant never sees another's data.
"""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.domain.billing import (
    InvoiceDocument,
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument, DpaAcceptanceDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)
from app.schemas.typings.assistants.prefixed_id import (
    AssistantVersionId,
    AutotestRunId,
)
from app.schemas.typings.billing.prefixed_id import InvoiceId, SubscriptionId
from app.schemas.typings.bookings.prefixed_id import (
    BookingId,
    LeadId,
    ResourceId,
    ScheduleExceptionId,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import CallId, ConversationId
from app.schemas.typings.conversations.strings import ChannelUserId, ProviderCallId
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import (
    OtpChallengeId,
    UserId,
    UserSessionId,
)
from app.schemas.typings.users.strings import AccessTokenHash


class UserRepoContract(RepoContract, Protocol):
    def save(self, user: UserDocument) -> None:
        raise NotImplementedError

    def get(self, user_id: UserId) -> UserDocument | None:
        raise NotImplementedError

    def find_by_phone_number(
        self,
        phone_number: E164PhoneNumber,
    ) -> UserDocument | None:
        raise NotImplementedError

    def find_by_email(self, email: EmailAddress) -> UserDocument | None:
        raise NotImplementedError


class OtpChallengeRepoContract(RepoContract, Protocol):
    def save(self, challenge: OtpChallengeDocument) -> None:
        raise NotImplementedError

    def get(self, challenge_id: OtpChallengeId) -> OtpChallengeDocument | None:
        raise NotImplementedError

    def list_created_since(
        self,
        created_after: Microseconds,
    ) -> list[OtpChallengeDocument]:
        """Challenges created after a moment (throttling of repeated logins)."""
        raise NotImplementedError


class UserSessionRepoContract(RepoContract, Protocol):
    def save(self, session: UserSessionDocument) -> None:
        raise NotImplementedError

    def find_by_token_hash(
        self,
        token_hash: AccessTokenHash,
    ) -> UserSessionDocument | None:
        raise NotImplementedError

    def delete(self, session_id: UserSessionId) -> None:
        raise NotImplementedError


class BusinessRepoContract(RepoContract, Protocol):
    def save(self, business: BusinessDocument) -> None:
        raise NotImplementedError

    def get(self, business_id: BusinessId) -> BusinessDocument | None:
        raise NotImplementedError

    def list_by_member(self, user_id: UserId) -> list[BusinessDocument]:
        """Businesses where the user is an owner or staff member."""
        raise NotImplementedError

    def list_all(self) -> list[BusinessDocument]:
        """Every business (platform admin views and background jobs only)."""
        raise NotImplementedError


class ChannelRepoContract(RepoContract, Protocol):
    def save(self, channel: ChannelDocument) -> None:
        raise NotImplementedError

    def get(self, channel_id: ChannelId) -> ChannelDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[ChannelDocument]:
        raise NotImplementedError

    def find_by_external_id(
        self,
        kind: ChannelKind,
        external_id: ChannelExternalId,
    ) -> ChannelDocument | None:
        """Resolve the tenant of an incoming webhook from the channel account."""
        raise NotImplementedError


class BusinessProfileRepoContract(RepoContract, Protocol):
    def save(self, profile: BusinessProfileDocument) -> None:
        raise NotImplementedError

    def get_by_business(
        self,
        business_id: BusinessId,
    ) -> BusinessProfileDocument | None:
        raise NotImplementedError


class KnowledgeItemRepoContract(RepoContract, Protocol):
    def save(self, item: KnowledgeItemDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        item_id: KnowledgeItemId,
    ) -> KnowledgeItemDocument | None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[KnowledgeItemDocument]:
        raise NotImplementedError

    def delete(self, business_id: BusinessId, item_id: KnowledgeItemId) -> None:
        raise NotImplementedError


class ResourceRepoContract(RepoContract, Protocol):
    def save(self, resource: ResourceDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        resource_id: ResourceId,
    ) -> ResourceDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[ResourceDocument]:
        raise NotImplementedError


class ScheduleExceptionRepoContract(RepoContract, Protocol):
    def save(self, exception: ScheduleExceptionDocument) -> None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[ScheduleExceptionDocument]:
        raise NotImplementedError

    def delete(
        self,
        business_id: BusinessId,
        exception_id: ScheduleExceptionId,
    ) -> None:
        raise NotImplementedError


class ContactRepoContract(RepoContract, Protocol):
    def save(self, contact: ContactDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        contact_id: ContactId,
    ) -> ContactDocument | None:
        raise NotImplementedError

    def find_by_channel_identity(
        self,
        business_id: BusinessId,
        channel: ChannelKind,
        channel_user_id: ChannelUserId,
    ) -> ContactDocument | None:
        raise NotImplementedError

    def find_by_phone_number(
        self,
        business_id: BusinessId,
        phone_number: E164PhoneNumber,
    ) -> ContactDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[ContactDocument]:
        raise NotImplementedError

    def delete(self, business_id: BusinessId, contact_id: ContactId) -> None:
        raise NotImplementedError


class ConversationRepoContract(RepoContract, Protocol):
    def save(self, conversation: ConversationDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> ConversationDocument | None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[ConversationDocument]:
        """Return conversations ordered by last_message_at descending."""
        raise NotImplementedError


class MessageRepoContract(RepoContract, Protocol):
    def save(self, message: MessageDocument) -> None:
        raise NotImplementedError

    def list_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> list[MessageDocument]:
        """Return messages ordered by created_at ascending."""
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[MessageDocument]:
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


class CallRepoContract(RepoContract, Protocol):
    def save(self, call: CallDocument) -> None:
        raise NotImplementedError

    def get(self, business_id: BusinessId, call_id: CallId) -> CallDocument | None:
        raise NotImplementedError

    def find_by_provider_call_id(
        self,
        business_id: BusinessId,
        provider_call_id: ProviderCallId,
    ) -> CallDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[CallDocument]:
        raise NotImplementedError


class BookingRepoContract(RepoContract, Protocol):
    def save(self, booking: BookingDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        booking_id: BookingId,
    ) -> BookingDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[BookingDocument]:
        """Return bookings ordered by starts_at ascending."""
        raise NotImplementedError


class LeadRepoContract(RepoContract, Protocol):
    def save(self, lead: LeadDocument) -> None:
        raise NotImplementedError

    def get(self, business_id: BusinessId, lead_id: LeadId) -> LeadDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[LeadDocument]:
        """Return leads ordered by created_at descending."""
        raise NotImplementedError


class HandoffRepoContract(RepoContract, Protocol):
    def save(self, handoff: HandoffDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        handoff_id: HandoffId,
    ) -> HandoffDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[HandoffDocument]:
        """Return handoffs ordered by created_at descending."""
        raise NotImplementedError


class UnansweredQuestionRepoContract(RepoContract, Protocol):
    def save(self, question: UnansweredQuestionDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        question_id: UnansweredQuestionId,
    ) -> UnansweredQuestionDocument | None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[UnansweredQuestionDocument]:
        """Return questions ordered by occurrence_count descending."""
        raise NotImplementedError


class AssistantVersionRepoContract(RepoContract, Protocol):
    def save(self, version: AssistantVersionDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        version_id: AssistantVersionId,
    ) -> AssistantVersionDocument | None:
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

    def get(
        self,
        business_id: BusinessId,
        run_id: AutotestRunId,
    ) -> AutotestRunDocument | None:
        raise NotImplementedError


class SubscriptionRepoContract(RepoContract, Protocol):
    def save(self, subscription: SubscriptionDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        subscription_id: SubscriptionId,
    ) -> SubscriptionDocument | None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[SubscriptionDocument]:
        raise NotImplementedError


class InvoiceRepoContract(RepoContract, Protocol):
    def save(self, invoice: InvoiceDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        invoice_id: InvoiceId,
    ) -> InvoiceDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[InvoiceDocument]:
        raise NotImplementedError


class UsageEventRepoContract(RepoContract, Protocol):
    def append(self, event: UsageEventDocument) -> None:
        raise NotImplementedError

    def list_by_business_between(
        self,
        business_id: BusinessId,
        occurred_from: Microseconds,
        occurred_to: Microseconds,
    ) -> list[UsageEventDocument]:
        """Events with occurred_from <= occurred_at < occurred_to."""
        raise NotImplementedError


class AuditLogRepoContract(RepoContract, Protocol):
    def append(self, entry: AuditLogEntryDocument) -> None:
        """Audit entries are never updated or deleted."""
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[AuditLogEntryDocument]:
        raise NotImplementedError


class DpaAcceptanceRepoContract(RepoContract, Protocol):
    def save(self, acceptance: DpaAcceptanceDocument) -> None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[DpaAcceptanceDocument]:
        raise NotImplementedError
