"""The accounts testbed's base: clock, settings, fakes and in-memory repositories."""

from collections.abc import Mapping

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.billing_repositories import SubscriptionRepository
from app.repositories.booking_repositories import (
    BookingRepository,
    HandoffRepository,
    LeadRepository,
)
from app.repositories.business_repositories import BusinessRepository
from app.repositories.call_repository import CallRepository
from app.repositories.compliance_repositories import (
    AuditLogRepository,
    DpaAcceptanceRepository,
)
from app.repositories.contact_activity_repository import ContactActivityRepository
from app.repositories.conversation_repositories import (
    ContactRepository,
    ConversationRepository,
    LlmTurnRepository,
    MessageRepository,
)
from app.repositories.customer_history_repository import CustomerHistoryRepository
from app.repositories.customer_repositories import (
    CustomerSegmentRepository,
    CustomerSettingsRepository,
)
from app.repositories.inbox_repositories import ConversationNoteRepository
from app.repositories.mfa_repositories import (
    MfaChallengeRepository,
    RecoveryCodeRepository,
    TotpFactorRepository,
)
from app.repositories.user_repositories import (
    OtpChallengeRepository,
    UserRepository,
    UserSessionRepository,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument, DpaAcceptanceDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.domain.customer_segments import CustomerSegmentDocument
from app.schemas.domain.customer_settings import CustomerSettingsDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.mfa import (
    MfaChallengeDocument,
    RecoveryCodeDocument,
    TotpFactorDocument,
)
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.foundation.support_access_builders import (
    in_memory_grant_repo,
    in_memory_platform_admin_repo,
)
from tests.users.accounts_clock import AdjustableClock
from tests.users.accounts_phones import PhonenumbersParser
from tests.users.accounts_recorders import (
    InMemoryRecordingStorage,
    RecordingOtpDelivery,
)
from tests.users.accounts_registries import (
    FakeCountryRegistry,
    FakeLanguageRegistry,
    FakeNicheTemplateRegistry,
)


class AccountsRepositories:
    """Every repository and fake of the accounts slice, over in-memory storage."""

    def __init__(self, environment_variables: Mapping[str, str]) -> None:
        self.clock: AdjustableClock = AdjustableClock()
        self.settings: AppSettings = assemble_app_settings(environment_variables)
        self.country_registry: FakeCountryRegistry = FakeCountryRegistry()
        self.language_registry: FakeLanguageRegistry = FakeLanguageRegistry()
        self.niche_registry: FakeNicheTemplateRegistry = FakeNicheTemplateRegistry()
        self.phone_parser: PhonenumbersParser = PhonenumbersParser()
        self.otp_delivery: RecordingOtpDelivery = RecordingOtpDelivery()
        self.recording_storage: InMemoryRecordingStorage = InMemoryRecordingStorage()

        self.user_collection = InMemoryDocumentCollectionAdapter[UserDocument](
            UserDocument
        )
        self.user_repo = UserRepository(self.user_collection)
        self.otp_challenge_repo = OtpChallengeRepository(
            InMemoryDocumentCollectionAdapter[OtpChallengeDocument](
                OtpChallengeDocument
            )
        )
        self.user_session_repo = UserSessionRepository(
            InMemoryDocumentCollectionAdapter[UserSessionDocument](UserSessionDocument)
        )
        self.business_repo = BusinessRepository(
            InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
        )
        self.audit_log_collection = InMemoryDocumentCollectionAdapter[
            AuditLogEntryDocument
        ](AuditLogEntryDocument)
        self.audit_log_repo = AuditLogRepository(self.audit_log_collection)
        self.dpa_acceptance_repo = DpaAcceptanceRepository(
            InMemoryDocumentCollectionAdapter[DpaAcceptanceDocument](
                DpaAcceptanceDocument
            )
        )
        self.contact_repo = ContactRepository(
            InMemoryDocumentCollectionAdapter[ContactDocument](ContactDocument)
        )
        conversations = InMemoryDocumentCollectionAdapter[ConversationDocument](
            ConversationDocument
        )
        self.conversation_repo = ConversationRepository(conversations)
        self.message_repo = MessageRepository(
            InMemoryDocumentCollectionAdapter[MessageDocument](MessageDocument)
        )
        self.llm_turn_repo = LlmTurnRepository(
            InMemoryDocumentCollectionAdapter[LlmTurnDocument](LlmTurnDocument)
        )
        calls = InMemoryDocumentCollectionAdapter[CallDocument](CallDocument)
        self.call_repo = CallRepository(calls)
        bookings = InMemoryDocumentCollectionAdapter[BookingDocument](BookingDocument)
        self.booking_repo = BookingRepository(bookings)
        leads = InMemoryDocumentCollectionAdapter[LeadDocument](LeadDocument)
        self.lead_repo = LeadRepository(leads)
        self.contact_activity_repo = ContactActivityRepository(
            conversations, bookings, leads
        )
        # Customers (1140): what customers did, segments, the team's settings.
        self.customer_history_repo = CustomerHistoryRepository(
            conversations, bookings, calls
        )
        self.customer_settings_repo = CustomerSettingsRepository(
            InMemoryDocumentCollectionAdapter[CustomerSettingsDocument](
                CustomerSettingsDocument
            )
        )
        self.customer_segment_repo = CustomerSegmentRepository(
            InMemoryDocumentCollectionAdapter[CustomerSegmentDocument](
                CustomerSegmentDocument
            )
        )
        self.handoff_repo = HandoffRepository(
            InMemoryDocumentCollectionAdapter[HandoffDocument](HandoffDocument)
        )
        self.conversation_note_repo = ConversationNoteRepository(
            InMemoryDocumentCollectionAdapter[ConversationNoteDocument](
                ConversationNoteDocument
            )
        )
        self.subscription_repo = SubscriptionRepository(
            InMemoryDocumentCollectionAdapter[SubscriptionDocument](
                SubscriptionDocument
            )
        )
        # Two-factor sign-in, and the session the HTTP gateway binds.
        self.totp_factor_repo = TotpFactorRepository(
            InMemoryDocumentCollectionAdapter[TotpFactorDocument](TotpFactorDocument)
        )
        self.recovery_code_repo = RecoveryCodeRepository(
            InMemoryDocumentCollectionAdapter[RecoveryCodeDocument](
                RecoveryCodeDocument
            )
        )
        self.mfa_challenge_repo = MfaChallengeRepository(
            InMemoryDocumentCollectionAdapter[MfaChallengeDocument](
                MfaChallengeDocument
            )
        )
        self.session_assurance = SessionAssuranceContext()
        # Platform access: the admin team and support's grants (1103).
        self.platform_admin_repo = in_memory_platform_admin_repo()
        self.grant_repo = in_memory_grant_repo()
