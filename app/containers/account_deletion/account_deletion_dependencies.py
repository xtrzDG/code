from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.billing import (
    PaymentGatewayAdapterContract,
    PaymentOrderRepoContract,
)
from app.contracts.business_erasure import (
    BusinessRowEraserAdapterContract,
    DeletionLedgerMirrorAdapterContract,
)
from app.contracts.channel_clients import TelegramBotApiClientContract
from app.contracts.channel_deprovisioning import MetaSubscriptionClientContract
from app.contracts.deletion_certificates import DeletionCertificateRendererContract
from app.contracts.export_archives import ExportArchiveStorageContract
from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.jobs import JobQueueFacilitatorContract, QueuedJobRepoContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.phone_numbers import (
    PhoneLineLockRegistryContract,
    PhoneNumberProvisionerAdapterContract,
    PhoneNumberRepoContract,
)
from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.processor_erasure import ProcessorErasureFacilitatorContract
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
    BusinessDeletionRepoContract,
)
from app.contracts.repositories.business_document_pages import (
    BusinessDocumentPagesContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import LlmTurnRepoContract
from app.contracts.repositories.mfa_repositories import (
    RecoveryCodeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.repositories.notification_repositories import (
    NotificationPreferencesRepoContract,
    PushSubscriptionRepoContract,
)
from app.contracts.repositories.passkey_repositories import PasskeyRepoContract
from app.contracts.repositories.security_nudge_repositories import (
    SecurityNudgeRepoContract,
)
from app.contracts.repositories.user_repositories import (
    UserRepoContract,
    UserSessionRepoContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.business_exports import BusinessExportDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import CallDocument, ConversationDocument
from app.schemas.domain.message_media import MessageMediaDocument
from app.schemas.domain.widget_uploads import WidgetUploadDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.operations.calendar_connection import (
    CalendarDisconnectResult,
    DisconnectCalendarCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId


@dataclass(frozen=True, slots=True, kw_only=True)
class AccountDeletionDependencies:
    """
    Everything closing and deleting a business, and deleting an account
    (R15-ACCOUNT-DELETION, migration 1220), takes from the rest of the
    application, as contracts: the closure and the ledger, the business's
    repositories (the deletion walks them page by page), the providers it
    switches off, the files it deletes, the person's sign-in records, and
    the row eraser of the platform pool. The only place the dependency
    graph meets the typed root (app/containers/use_cases/
    account_deletion_root_provider.py fills it).
    """

    # Closing a business and its ledger.
    authorize_business_access: UseCaseContract[BusinessAccessRequest, BusinessDocument]
    step_up: StepUpGuardContract
    storage_scope: StorageScopeContract
    closure_repo: BusinessClosureRepoContract
    deletion_repo: BusinessDeletionRepoContract
    business_repo: BusinessRepoContract
    channel_repo: ChannelRepoContract
    brand_repo: BrandRepoContract
    user_repo: UserRepoContract
    audit_log_repo: AuditLogRepoContract
    subscription_repo: SubscriptionRepoContract
    invoice_repo: InvoiceRepoContract
    payment_gateway: PaymentGatewayAdapterContract
    payment_order_repo: PaymentOrderRepoContract
    remove_voice_agent: UseCaseContract[BusinessId, None]
    resume_assistant: UseCaseContract[BusinessDocument, None]
    manager_notifier: ManagerNotificationFacilitatorContract
    localized_text_resolver: LocalizedTextResolverContract
    job_queue: JobQueueFacilitatorContract
    job_repo: QueuedJobRepoContract
    # The deletion: providers, files, traces, rows.
    assistant_version_repo: AssistantVersionRepoContract
    disconnect_google_calendar: UseCaseContract[
        DisconnectCalendarCommand, CalendarDisconnectResult
    ]
    phone_number_repo: PhoneNumberRepoContract
    phone_number_provisioner: PhoneNumberProvisionerAdapterContract
    phone_line_lock: PhoneLineLockRegistryContract
    secret_cipher: SecretCipherAdapterContract
    telegram_client: TelegramBotApiClientContract
    meta_subscriptions: MetaSubscriptionClientContract
    conversation_pages: BusinessDocumentPagesContract[ConversationDocument]
    call_pages: BusinessDocumentPagesContract[CallDocument]
    message_media_pages: BusinessDocumentPagesContract[MessageMediaDocument]
    widget_upload_pages: BusinessDocumentPagesContract[WidgetUploadDocument]
    business_export_pages: BusinessDocumentPagesContract[BusinessExportDocument]
    llm_turn_repo: LlmTurnRepoContract
    recording_storage: RecordingStorageAdapterContract
    media_storage: MediaStorageAdapterContract
    export_archive_storage: ExportArchiveStorageContract
    processor_erasure: ProcessorErasureFacilitatorContract
    row_eraser: BusinessRowEraserAdapterContract
    ledger_mirror: DeletionLedgerMirrorAdapterContract
    certificate_renderer: DeletionCertificateRendererContract
    # Deleting an account.
    user_session_repo: UserSessionRepoContract
    totp_factor_repo: TotpFactorRepoContract
    recovery_code_repo: RecoveryCodeRepoContract
    passkey_repo: PasskeyRepoContract
    push_subscription_repo: PushSubscriptionRepoContract
    notification_preferences_repo: NotificationPreferencesRepoContract
    security_nudge_repo: SecurityNudgeRepoContract
    platform_admins: PlatformAdminRegistryContract
    app_settings: AppSettings
    wall_clock: WallClock[Microseconds]
