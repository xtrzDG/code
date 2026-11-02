"""The admin's global pause over in-memory stores, with admins by role."""

from dataclasses import dataclass, field

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.registries.limits.platform_spend_gauge_registry import (
    PlatformSpendGaugeRegistry,
)
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.platform_safety_repositories import PlatformPauseRepository
from app.repositories.spend_guard_repositories import UsageSpendRepository
from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.constants.access import PlatformAdminRole
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.platform_pauses import PlatformPauseDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.spend_guard.platform_pause.get_platform_pause_use_case import (
    GetPlatformPauseUseCase,
)
from app.use_cases.spend_guard.platform_pause.set_platform_pause_use_case import (
    SetPlatformPauseUseCase,
)
from app.utilities.security.admin_permissions import has_permission
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.compliance.audit_repositories import audit_log_repository

NOW: Microseconds = Microseconds(1_793_620_800_000_000)  # 2026-11-02 12:00 UTC


class AdminsByRole(UseCaseContract[PlatformAdminAccessRequest, UserDocument]):
    """The platform admin check with the real role permissions."""

    def __init__(self, roles: dict[UserId, PlatformAdminRole]) -> None:
        self._roles: dict[UserId, PlatformAdminRole] = roles

    def run(self, input_data: PlatformAdminAccessRequest) -> UserDocument:
        role: PlatformAdminRole | None = self._roles.get(input_data.user_id)
        if role is None or not has_permission(role, input_data.permission):
            raise AccessDeniedError("Your platform admin role does not include this.")
        return UserDocument.model_construct(id=input_data.user_id)


class StepUp(StepUpGuardContract):
    def __init__(self) -> None:
        self.is_recent: bool = True

    def require_recent_authentication(self) -> None:
        if not self.is_recent:
            raise StepUpRequiredError("Confirm it is you to do this.")


@dataclass
class PauseWorld:
    super_admin: UserId = field(default_factory=UserId)
    support: UserId = field(default_factory=UserId)
    billing: UserId = field(default_factory=UserId)
    step_up: StepUp = field(default_factory=StepUp)
    usage_events: InMemoryDocumentCollectionAdapter[UsageEventDocument] = field(
        default_factory=lambda: InMemoryDocumentCollectionAdapter(UsageEventDocument)
    )
    pauses: PlatformPauseRepository = field(
        default_factory=lambda: PlatformPauseRepository(
            InMemoryDocumentCollectionAdapter(PlatformPauseDocument)
        )
    )
    audit_entries: InMemoryDocumentCollectionAdapter[AuditLogEntryDocument] = field(
        default_factory=lambda: InMemoryDocumentCollectionAdapter(AuditLogEntryDocument)
    )
    settings: SpendGuardSettings = field(default_factory=SpendGuardSettings)

    @property
    def audit(self) -> AuditLogRepository:
        return audit_log_repository(self.audit_entries)

    def platform_entries(self) -> list[AuditLogEntryDocument]:
        """The entries that name no business, in the order written."""

        return [e for e in self.audit_entries.list_all() if e.business_id is None]

    def admins(self) -> AdminsByRole:
        return AdminsByRole(
            {
                self.super_admin: PlatformAdminRole.SUPER,
                self.support: PlatformAdminRole.SUPPORT_READONLY,
                self.billing: PlatformAdminRole.BILLING,
            }
        )

    def gauge(self) -> PlatformSpendGaugeRegistry:
        return PlatformSpendGaugeRegistry(
            UsageSpendRepository(self.usage_events), StorageScopeContext()
        )

    def wall_clock(self) -> WallClock[Microseconds]:
        return WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: int(NOW) * 1_000,
        )

    def get_use_case(self) -> GetPlatformPauseUseCase:
        return GetPlatformPauseUseCase(
            self.admins(), self.pauses, self.gauge(), self.settings, self.wall_clock()
        )

    def set_use_case(self) -> SetPlatformPauseUseCase:
        return SetPlatformPauseUseCase(
            self.admins(),
            self.pauses,
            self.gauge(),
            self.audit,
            self.step_up,
            self.settings,
            self.wall_clock(),
        )
