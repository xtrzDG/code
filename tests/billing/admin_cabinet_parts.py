"""The admin's audited look into a client's cabinet, wired for the testbed."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.repositories.support_access_grant_repository import (
    SupportAccessGrantRepository,
)
from app.use_cases.admin.open_client_cabinet_use_case import OpenClientCabinetUseCase
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.foundation.access_support import AllowStepUp, AuthorizeFlaggedAdmin
from tests.foundation.support_access_builders import (
    RecordingStaffAlerts,
    in_memory_grant_repo,
    in_memory_platform_admins,
)


def build_open_client_cabinet(
    authorize_admin: AuthorizeFlaggedAdmin,
    business_repo: BusinessRepoContract,
    audit_log_repo: AuditLogRepoContract,
    wall_clock: WallClock[Microseconds],
) -> tuple[
    SupportAccessGrantRepository, RecordingStaffAlerts, OpenClientCabinetUseCase
]:
    """The support grants, the owners' alerts and the use case that opens."""

    grants = in_memory_grant_repo()
    alerts = RecordingStaffAlerts()
    return (
        grants,
        alerts,
        OpenClientCabinetUseCase(
            authorize_platform_admin=authorize_admin,
            platform_admins=in_memory_platform_admins(wall_clock),
            business_repo=business_repo,
            grant_repo=grants,
            audit_log_repo=audit_log_repo,
            staff_alerts=alerts,
            localized_text_resolver=LocalizedTextResolver(),
            wall_clock=wall_clock,
            step_up=AllowStepUp(),
        ),
    )
