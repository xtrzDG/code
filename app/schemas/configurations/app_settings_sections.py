"""
The grouped sections of the runtime settings (AppSettings extends them):
each a settings object of its own, read as `app_settings.<section>`.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.configurations.backup_settings import BackupSettings
from app.schemas.configurations.embedding_settings import EmbeddingSettings
from app.schemas.configurations.garbage_collection_settings import (
    GarbageCollectionSettings,
)
from app.schemas.configurations.growth_settings import GrowthSettings
from app.schemas.configurations.media_settings import MediaSettings
from app.schemas.configurations.payment_settings import PaymentSettings
from app.schemas.configurations.phone_number_settings import PhoneNumberSettings
from app.schemas.configurations.platform_alert_settings import PlatformAlertSettings
from app.schemas.configurations.privacy_settings import PrivacySettings
from app.schemas.configurations.public_api_settings import PublicApiSettings
from app.schemas.configurations.public_site_settings import PublicSiteSettings
from app.schemas.configurations.quality_settings import QualitySettings
from app.schemas.configurations.reply_safety_settings import ReplySafetySettings
from app.schemas.configurations.reply_speed_settings import ReplySpeedSettings
from app.schemas.configurations.seller_settings import SellerSettings
from app.schemas.configurations.session_settings import SessionSettings
from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.configurations.support_settings import SupportSettings
from app.schemas.configurations.telemetry_settings import TelemetrySettings


class AppSettingsSections(ImmutableDTO):
    """The settings that come as sections, each with its defaults."""

    # Off-site backups and the restore drill (BACKUP_*; `workshop backup`,
    # `workshop restore-check`, docs/operations/backup-restore.md).
    backup: BackupSettings = Field(default_factory=BackupSettings)
    # Voice notes and photos of customers (LLM_TRANSCRIBE_MODEL, MEDIA_MAX_*).
    media: MediaSettings = Field(default_factory=MediaSettings)
    embeddings: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    # Bursts, turn deadline, failover (MESSAGE_COALESCE_*, CHAT_TURN_*, LLM_FALLBACK_*).
    reply_speed: ReplySpeedSettings = Field(default_factory=ReplySpeedSettings)
    # pass^k of autotests and the nightly judging of real conversations.
    quality: QualitySettings = Field(default_factory=QualitySettings)
    # The reply guard's claim check and injection brake (LLM_VERIFIER_*, INJECTION_*).
    reply_safety: ReplySafetySettings = Field(default_factory=ReplySafetySettings)
    # Where the platform alerts go (PLATFORM_ALERT_*, docs/operations/slo.md).
    platform_alerts: PlatformAlertSettings = Field(
        default_factory=PlatformAlertSettings
    )
    # When sessions end (SESSION_IDLE_TIMEOUT_SECONDS, ADMIN_SESSION_*).
    sessions: SessionSettings = Field(default_factory=SessionSettings)
    # The cabinet's "Help and support" contacts (SUPPORT_*).
    support: SupportSettings = Field(default_factory=SupportSettings)
    # The suppression list's key and the full exports' one-time links
    # (SUPPRESSION_LIST_KEY, EXPORT_DOWNLOAD_LINK_MINUTES).
    privacy: PrivacySettings = Field(default_factory=PrivacySettings)
    # The seller on invoices and its VAT (SELLER_*, PLATFORM_VAT_REGISTERED).
    seller: SellerSettings = Field(default_factory=SellerSettings)
    # Landing-page sandbox demos, legal pages (PUBLIC_DEMO_*, LEGAL_TEXTS_FINAL).
    public_site: PublicSiteSettings = Field(default_factory=PublicSiteSettings)
    # Spend limits, call caps, API limits (SPEND_*, CALL_*, API_*, PLATFORM_*).
    spend_guard: SpendGuardSettings = Field(default_factory=SpendGuardSettings)
    growth: GrowthSettings = Field(default_factory=GrowthSettings)
    telemetry: TelemetrySettings = Field(default_factory=TelemetrySettings)
    public_api: PublicApiSettings = Field(default_factory=PublicApiSettings)
    payments: PaymentSettings = Field(default_factory=PaymentSettings)  # STRIPE_*
    phone_numbers: PhoneNumberSettings = Field(default_factory=PhoneNumberSettings)
    # The startup heap frozen after warm-up, the collector's thresholds
    # (GC_FREEZE_AFTER_WARMUP, GC_THRESHOLDS; docs/operations/capacity.md).
    garbage_collection: GarbageCollectionSettings = Field(
        default_factory=GarbageCollectionSettings
    )
