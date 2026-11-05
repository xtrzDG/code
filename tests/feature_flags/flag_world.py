"""The feature flags over in-memory stores, with admins by role (REL-08)."""

from dataclasses import dataclass, field

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.feature_flag_repository import FeatureFlagRepository
from app.schemas.constants.access import PlatformAdminRole
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.feature_flags import FeatureFlagDocument
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.feature_flags.check_feature_flag_use_case import (
    CheckFeatureFlagUseCase,
)
from app.use_cases.admin.feature_flags.list_feature_flags_use_case import (
    ListFeatureFlagsUseCase,
)
from app.use_cases.admin.feature_flags.set_feature_flag_use_case import (
    SetFeatureFlagUseCase,
)
from app.utilities.feature_flags.feature_flag_gate import FeatureFlagGate
from tests.compliance.audit_repositories import audit_log_repository
from tests.spend_guard.platform_pause_world import NOW, AdminsByRole, StepUp


@dataclass
class FlagWorld:
    super_admin: UserId = field(default_factory=UserId)
    support: UserId = field(default_factory=UserId)
    step_up: StepUp = field(default_factory=StepUp)
    flags: FeatureFlagRepository = field(
        default_factory=lambda: FeatureFlagRepository(
            InMemoryDocumentCollectionAdapter(FeatureFlagDocument)
        )
    )
    audit_entries: InMemoryDocumentCollectionAdapter[AuditLogEntryDocument] = field(
        default_factory=lambda: InMemoryDocumentCollectionAdapter(AuditLogEntryDocument)
    )

    @property
    def audit(self) -> AuditLogRepository:
        return audit_log_repository(self.audit_entries)

    def admins(self) -> AdminsByRole:
        return AdminsByRole(
            {
                self.super_admin: PlatformAdminRole.SUPER,
                self.support: PlatformAdminRole.SUPPORT_READONLY,
            }
        )

    def wall_clock(self) -> WallClock[Microseconds]:
        return WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: int(NOW) * 1_000,
        )

    def list_use_case(self) -> ListFeatureFlagsUseCase:
        return ListFeatureFlagsUseCase(self.admins(), self.flags)

    def set_use_case(self) -> SetFeatureFlagUseCase:
        return SetFeatureFlagUseCase(
            self.admins(), self.flags, self.audit, self.step_up, self.wall_clock()
        )

    def check_use_case(self) -> CheckFeatureFlagUseCase:
        return CheckFeatureFlagUseCase(self.admins(), FeatureFlagGate(self.flags))
