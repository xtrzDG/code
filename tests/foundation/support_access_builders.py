"""
The access check of tests, wired as in production: members by the
business, platform support only during an open look into the cabinet
(grants in memory), admin roles from an in-memory admin team bootstrapped
from the settings' PLATFORM_ADMIN_* lists.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.notifications import (
    StaffAlertFacilitatorContract,
    StaffAlertTextsContract,
)
from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.support_access import (
    SignInNoticeFacilitatorContract,
    SupportAccessGrantRepoContract,
)
from app.registries.access.platform_admin_registry import PlatformAdminRegistry
from app.repositories.platform_admin_repository import PlatformAdminRepository
from app.repositories.support_access_grant_repository import (
    SupportAccessGrantRepository,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.access import SupportAccessKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.platform_admins import PlatformAdminDocument
from app.schemas.domain.support_access_grants import SupportAccessGrantDocument
from app.schemas.domain.users import UserDocument, UserSessionDocument
from app.schemas.dto.notifications.staff_alerts import StaffAlert, StaffAlertBrief
from app.schemas.typings.access.constrained_strings import SupportAccessReason
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId, UserSessionId
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.authorize_support_access_use_case import (
    AuthorizeSupportAccessUseCase,
)
from tests.foundation.access_support import ACCESS_SETTINGS

HOUR_MICROSECONDS: int = 60 * 60 * 1_000_000


def in_memory_grant_repo() -> SupportAccessGrantRepository:
    return SupportAccessGrantRepository(
        InMemoryDocumentCollectionAdapter[SupportAccessGrantDocument](
            SupportAccessGrantDocument
        )
    )


def in_memory_platform_admin_repo() -> PlatformAdminRepository:
    return PlatformAdminRepository(
        InMemoryDocumentCollectionAdapter[PlatformAdminDocument](PlatformAdminDocument)
    )


def in_memory_platform_admins(
    wall_clock: WallClock[Microseconds],
    settings: AppSettings = ACCESS_SETTINGS,
    platform_admin_repo: PlatformAdminRepository | None = None,
) -> PlatformAdminRegistry:
    """Roles from an empty team: the settings' lists bootstrap SUPER admins."""

    return PlatformAdminRegistry(
        platform_admin_repo=platform_admin_repo or in_memory_platform_admin_repo(),
        app_settings=settings,
        wall_clock=wall_clock,
    )


def build_authorize_business_access(
    business_repo: BusinessRepoContract,
    user_repo: UserRepoContract,
    audit_log_repo: AuditLogRepoContract,
    wall_clock: WallClock[Microseconds],
    session_assurance: SessionAssuranceContract,
    app_settings: AppSettings = ACCESS_SETTINGS,
    grant_repo: SupportAccessGrantRepoContract | None = None,
    platform_admins: PlatformAdminRegistryContract | None = None,
) -> AuthorizeBusinessAccessUseCase:
    """The production access check over these repositories."""

    return AuthorizeBusinessAccessUseCase(
        business_repo=business_repo,
        session_assurance=session_assurance,
        authorize_support_access=AuthorizeSupportAccessUseCase(
            user_repo=user_repo,
            platform_admins=platform_admins
            or in_memory_platform_admins(wall_clock, app_settings),
            grant_repo=grant_repo or in_memory_grant_repo(),
            audit_log_repo=audit_log_repo,
            session_assurance=session_assurance,
            wall_clock=wall_clock,
        ),
    )


def open_support_session(
    grant_repo: SupportAccessGrantRepoContract,
    business_id: BusinessId,
    admin_id: UserId,
    now: int,
    reason: str = "Owner asked for help with bookings",
) -> SupportAccessGrantDocument:
    """A platform admin's open look into the cabinet for the next hour."""

    grant = SupportAccessGrantDocument(
        business_id=business_id,
        kind=SupportAccessKind.SESSION,
        granted_by=admin_id,
        admin_user_id=admin_id,
        reason=SupportAccessReason(reason),
        expires_at=Microseconds(now + HOUR_MICROSECONDS),
        created_at=Microseconds(now),
        updated_at=Microseconds(now),
    )
    grant_repo.save(grant)
    return grant


def allow_support_changes(
    grant_repo: SupportAccessGrantRepoContract,
    business_id: BusinessId,
    owner_id: UserId,
    now: int,
    hours: int = 24,
) -> SupportAccessGrantDocument:
    """The owner's consent to support's changes for some hours."""

    consent = SupportAccessGrantDocument(
        business_id=business_id,
        kind=SupportAccessKind.WRITE_CONSENT,
        granted_by=owner_id,
        expires_at=Microseconds(now + hours * HOUR_MICROSECONDS),
        created_at=Microseconds(now),
        updated_at=Microseconds(now),
    )
    grant_repo.save(consent)
    return consent


class RecordingSignInNotices(SignInNoticeFacilitatorContract):
    """Records the sessions a new-device notice was asked about."""

    def __init__(self) -> None:
        self.noticed: list[tuple[UserId, UserSessionId, int]] = []

    def notice_new_device(
        self,
        user: UserDocument,
        session: UserSessionDocument,
        other_sessions: Sequence[UserSessionDocument],
    ) -> None:
        self.noticed.append((user.id, session.id, len(other_sessions)))


class RecordingStaffAlerts(StaffAlertFacilitatorContract):
    """Records each alert with its English brief; nothing is sent."""

    def __init__(self) -> None:
        self.alerts: list[tuple[StaffAlert, StaffAlertBrief]] = []

    def alert(
        self,
        business: BusinessDocument,
        alert: StaffAlert,
        texts: StaffAlertTextsContract,
    ) -> DeliveredNotificationCount:
        del business
        self.alerts.append((alert, texts.brief(LanguageTag("en"))))
        return DeliveredNotificationCount(1)
