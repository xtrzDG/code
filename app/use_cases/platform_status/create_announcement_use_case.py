from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_status import PlatformAnnouncementRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.platform_status import PlatformAnnouncementDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.dto.platform_announcements import (
    AnnouncementAdminView,
    CreateAnnouncementCommand,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.use_cases.platform_status.announcement_audit import audit_announcement
from app.use_cases.platform_status.announcement_views import (
    admin_view,
    stored_messages,
)

# A planned maintenance may be announced this far ahead at most.
MAX_LEAD_MICROSECONDS: int = 60 * 24 * 60 * 60 * 1_000_000


class CreateAnnouncementUseCase(
    UseCaseContract[CreateAnnouncementCommand, AnnouncementAdminView]
):
    """
    POST /v1/admin/announcements: a platform admin tells every owner what
    is happening (an outage, slow answers, planned maintenance) in the
    cabinet's banner and on the public status page; its level counts for
    the components it names from its start until it is resolved.

    Needs MANAGE_OPERATIONS and a recent sign-in (step-up), like every
    admin action that reaches every owner; audited platform-wide.

    Raises:
        AccessDeniedError: not a platform admin who manages operations.
        StepUpRequiredError: the session must sign in again first.
        ValidationFailedError: the start is in the past by more than the
            check allows, too far ahead, or after the expected end.
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

    def run(self, input_data: CreateAnnouncementCommand) -> AnnouncementAdminView:
        admin: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_OPERATIONS,
            )
        )
        self._step_up.require_recent_authentication()
        now: Microseconds = self._wall_clock.now_unix()
        body = input_data.body
        starts_at: Microseconds = body.starts_at or now
        if int(starts_at) > int(now) + MAX_LEAD_MICROSECONDS:
            raise ValidationFailedError(
                "An announcement starts within the next 60 days."
            )
        if body.expected_end_at is not None and int(body.expected_end_at) <= max(
            int(starts_at), int(now)
        ):
            raise ValidationFailedError(
                "An announcement is expected to end after it starts and after now."
            )

        announcement = PlatformAnnouncementDocument(
            level=body.level,
            components=list(body.components),
            messages=stored_messages(body.messages),
            starts_at=starts_at,
            expected_end_at=body.expected_end_at,
            created_by=admin.id,
            created_at=now,
            updated_at=now,
        )
        self._announcement_repo.save(announcement)
        audit_announcement(
            self._audit_log_repo,
            announcement,
            AuditAction.CREATE,
            admin.id,
            input_data.client_ip_address,
            now,
        )
        return admin_view(announcement)
