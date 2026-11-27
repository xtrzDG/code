"""
The renewal of WhatsApp Embedded Signup tokens wired in memory: a business
and its channels behind the system health repository, Meta's token
endpoints scripted per token on the real Graph client and its circuit
breaker, a cipher whose every sealing differs (so a key rotation's reseal
can be told from a reconnect), and recorders of what the owners and the
open cabinets are told.
"""

from typed_time_provider import Microseconds

from app.adapters.channels.circuit_breaking_meta_token_refresh_adapter import (
    CircuitBreakingMetaTokenRefreshAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.clients.meta.meta_oauth_client import MetaOAuthClient
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.repositories.business_repositories import (
    BusinessRepository,
    ChannelRepository,
)
from app.repositories.system_health_repository import SystemHealthRepository
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.resilience import OutboundProvider
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.jobs import QueuedJobDocument, WorkerHeartbeatDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelExternalId, ChannelSecret
from app.schemas.typings.meta_connection.constrained_strings import (
    WhatsAppBusinessAccountId,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.channels.meta_connection.refresh_whatsapp_tokens_use_case import (
    RefreshWhatsAppTokensUseCase,
)
from app.use_cases.channels.meta_connection.whatsapp_token_notices import (
    WhatsAppTokenNotices,
)
from app.use_cases.channels.meta_connection.whatsapp_token_refresh import (
    WhatsAppTokenRefresh,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.resilience.provider_circuits import provider_circuit
from tests.compliance.audit_repositories import audit_log_repository
from tests.live_events.recording_event_publisher import RecordingEventPublisher
from tests.meta_connection.token_refresh_fakes import (
    WABA_ID,
    FlakyChannelRepo,
    HookedCredentialWatch,
    RecordingOwnerEmails,
    RecordingStaffAlerts,
    ResealingCipher,
    ScriptedMetaTokens,
)
from tests.platform_ops.ops_documents import DAY, HOUR, at, business, member
from tests.platform_ops.ops_world import OpsClock
from tests.resilience.test_circuit_breaker import Ticks

APP_ID: str = "1234567890"
APP_SECRET: str = "test-app-secret-0000"  # gitleaks:allow
OLD_TOKEN: str = "EAAfake-token-1"
NEW_TOKEN: str = "EAAfake-token-2"
TICK = JobTick(job_name=JobName("refresh_whatsapp_tokens"), scheduled_at=at(0))


class TokenRefreshWorld:
    """One business with an owner, its channels and the job that renews tokens."""

    def __init__(self, refresh_days: str = "15", has_meta_app: bool = True) -> None:
        self.clock = OpsClock()
        self.channels = InMemoryDocumentCollectionAdapter[ChannelDocument](
            ChannelDocument
        )
        self.businesses = InMemoryDocumentCollectionAdapter[BusinessDocument](
            BusinessDocument
        )
        self.channel_repo = ChannelRepository(self.channels)
        # What the job reads and writes through: tests break it per channel.
        self.flaky_channels = FlakyChannelRepo(self.channel_repo)
        self.watch = HookedCredentialWatch(
            SystemHealthRepository(
                InMemoryDocumentCollectionAdapter(QueuedJobDocument),
                InMemoryDocumentCollectionAdapter(WorkerHeartbeatDocument),
                self.channels,
                self.businesses,
            )
        )
        self.business_repo = BusinessRepository(self.businesses)
        self.audit = audit_log_repository()
        self.cipher = ResealingCipher()
        self.meta = ScriptedMetaTokens()
        self.live_events = RecordingEventPublisher()
        self.alerts = RecordingStaffAlerts()
        self.emails = RecordingOwnerEmails()
        self.business: BusinessDocument = business(
            "Funicular VR", member(UserId(), BusinessMemberRole.OWNER)
        )
        self.business_repo.save(self.business)
        environment: dict[str, str] = {"META_TOKEN_REFRESH_DAYS": refresh_days}
        if has_meta_app:
            environment |= {"META_APP_ID": APP_ID, "META_APP_SECRET": APP_SECRET}
        oauth = MetaOAuthClient(transport=self.meta.build())
        self.use_case = RefreshWhatsAppTokensUseCase(
            credential_watch=self.watch,
            business_repo=self.business_repo,
            channel_repo=self.flaky_channels,
            live_events=self.live_events,
            token_refresh=WhatsAppTokenRefresh(
                channel_repo=self.flaky_channels,
                secret_cipher=self.cipher,
                refresh_client=CircuitBreakingMetaTokenRefreshAdapter(
                    inner_client=oauth,
                    circuit_breaker=CircuitBreakerFacilitator(Ticks().clock()),
                    circuit=provider_circuit(OutboundProvider.META),
                ),
                oauth_client=oauth,
                audit_log_repo=self.audit,
            ),
            notices=WhatsAppTokenNotices(
                self.alerts, self.emails, LocalizedTextResolver()
            ),
            app_settings=assemble_app_settings(environment),
            wall_clock=self.clock.wall_clock,
        )
        self._numbers: int = 0

    def add_whatsapp(
        self,
        token: str | None,
        ends_at: Microseconds | None,
        status: ChannelStatus = ChannelStatus.CONNECTED,
        kind: ChannelKind = ChannelKind.WHATSAPP,
        business_id: BusinessId | None = None,
    ) -> ChannelDocument:
        """A channel connected 50 days ago with its own token (None: by hand)."""

        self._numbers += 1
        channel = ChannelDocument(
            business_id=business_id or self.business.id,
            kind=kind,
            status=status,
            external_id=ChannelExternalId(f"1065403522{self._numbers:05d}"),
            encrypted_secret=(
                None if token is None else self.cipher.encrypt(ChannelSecret(token))
            ),
            whatsapp_business_account_id=(
                WhatsAppBusinessAccountId(WABA_ID)
                if kind is ChannelKind.WHATSAPP
                else None
            ),
            credential_expires_at=ends_at,
            credential_checked_at=at(-HOUR),
            created_at=at(-50 * DAY),
            updated_at=at(-HOUR),
        )
        self.channel_repo.save(channel)
        return channel

    def run(self) -> int:
        """One run of the job, now; how many items it processed."""

        return int(self.use_case.run(TICK).processed_count)

    def stored(self, channel: ChannelDocument) -> ChannelDocument:
        found: ChannelDocument | None = self.channel_repo.get(channel.id)
        assert found is not None
        return found

    def token_of(self, channel: ChannelDocument) -> str | None:
        sealed = self.stored(channel).encrypted_secret
        return None if sealed is None else str(self.cipher.decrypt(sealed))

    def audit_entries(self) -> list[AuditLogEntryDocument]:
        return self.audit.list_by_business(self.business.id)
