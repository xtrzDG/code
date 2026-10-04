from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_status import PlatformAnnouncementRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.platform_status import (
    AnnouncementLevel,
    AnnouncementStatus,
)
from app.schemas.domain.platform_status import PlatformAnnouncementDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.dto.platform_announcements import (
    AnnouncementAdminView,
    UpdateAnnouncementCommand,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.use_cases.platform_status.announcement_audit import audit_announcement
from app.use_cases.platform_status.announcement_views import (
    admin_view,
    stored_messages,
)


class UpdateAnnouncementUseCase(
    UseCaseContract[UpdateAnnouncementCommand, AnnouncementAdminView]
):
    """
    PATCH /v1/admin/announcements/{id}: the team says more as it learns
    (a new level, other components, new texts, a new expected end) or
    resolves it (`resolve: true`): the banner disappears and the status
    page lists it under past announcements. A resolved announcement
    cannot change any more. Same access and audit as creating one.

    Raises:
        NotFoundError: no such announcement.
        ConflictError: it was resolved already.
        ValidationFailedError: a level other than INFO without components.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        announcement_repo: PlatformAnnouncementRepoContract,
        audit_log_repo: AuditLogRepoContract,
        step_up: StepUpGuardContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._announcement_repo: PlatformAnnouncementRepoContract = announcement_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._step_up: StepUpGuardContract = step_up
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateAnnouncementCommand) -> AnnouncementAdminView:
        admin: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_OPERATIONS,
            )
        )
        self._step_up.require_recent_authentication()
        announcement: PlatformAnnouncementDocument | None = self._announcement_repo.get(
            input_data.announcement_id
        )
        if announcement is None:
            raise NotFoundError("There is no such announcement.")
        if announcement.status is AnnouncementStatus.RESOLVED:
            raise ConflictError("The announcement was resolved already.")

        now: Microseconds = self._wall_clock.now_unix()
        body = input_data.body
        level: AnnouncementLevel = body.level or announcement.level
        components = (
            list(body.components)
            if body.components is not None
            else list(announcement.components)
        )
        if level is not AnnouncementLevel.INFO and not components:
            raise ValidationFailedError(
                "Maintenance, degraded service and outages name the components "
                "they affect."
            )
        if body.expected_end_at is not None and int(body.expected_end_at) <= max(
            int(announcement.starts_at), int(now)
        ):
            raise ValidationFailedError(
                "An announcement is expected to end after it starts and after now."
            )

        changed = announcement.model_copy(
            update={
                "level": level,
                "components": components,
                "messages": (
                    stored_messages(body.messages)
                    if body.messages is not None
                    else announcement.messages
                ),
                "expected_end_at": body.expected_end_at or announcement.expected_end_at,
                "status": (
                    AnnouncementStatus.RESOLVED if body.resolve else announcement.status
                ),
                "resolved_at": now if body.resolve else None,
                "updated_by": admin.id,
                "updated_at": now,
            }
        )
        self._announcement_repo.save(changed)
        audit_announcement(
            self._audit_log_repo,
            changed,
            AuditAction.UPDATE,
            admin.id,
            input_data.client_ip_address,
            now,
        )
        return admin_view(changed)
