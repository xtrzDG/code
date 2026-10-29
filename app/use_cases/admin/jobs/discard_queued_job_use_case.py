from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import QueuedJobRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.jobs import QueuedJobStatus
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin_jobs import AdminJobActionResult, AdminJobCommand
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import ConflictError
from app.utilities.jobs.queued_job_views import (
    build_job_audit_entry,
    build_queued_job_view,
)

DISCARDABLE_STATUSES: frozenset[QueuedJobStatus] = frozenset(
    {QueuedJobStatus.DEAD, QueuedJobStatus.PENDING}
)


class DiscardQueuedJobUseCase(UseCaseContract[AdminJobCommand, AdminJobActionResult]):
    """
    A platform admin drops a dead job, or a waiting one that must not run
    (e.g. it keeps failing on a provider that is gone): it turns DISCARDED,
    is never run again unless retried, and is purged with the finished jobs
    after 30 days. Written to the audit log (DELETE of the queued job, in
    the job's business log when it has a business).

    Raises:
        AccessDeniedError: the user is not a platform admin.
        NotFoundError: there is no such job.
        ConflictError: the job runs right now, is done or already discarded.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        job_repo: QueuedJobRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._job_repo: QueuedJobRepoContract = job_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AdminJobCommand) -> AdminJobActionResult:
        admin: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_OPERATIONS,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()

        def discard(job: QueuedJobDocument) -> None:
            if job.status not in DISCARDABLE_STATUSES:
                raise ConflictError(
                    f"Job {job.id} is {job.status.value}; only dead or waiting "
                    "jobs can be discarded."
                )

            job.status = QueuedJobStatus.DISCARDED
            job.updated_at = now

        discarded: QueuedJobDocument = self._job_repo.update(input_data.job_id, discard)
        entry: AuditLogEntryDocument = build_job_audit_entry(
            admin.id,
            discarded,
            AuditAction.DELETE,
            input_data.client_ip_address,
            now,
        )
        self._audit_log_repo.append(entry)
        return AdminJobActionResult(
            job=build_queued_job_view(discarded),
            audit_log_entry_id=entry.id,
        )
