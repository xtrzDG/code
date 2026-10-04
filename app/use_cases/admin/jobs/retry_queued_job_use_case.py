from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobWakeupContract, QueuedJobRepoContract
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
from app.schemas.typings.platform.constrained_integers import JobAttemptCount
from app.utilities.jobs.queued_job_views import (
    build_job_audit_entry,
    build_queued_job_view,
)

RETRYABLE_STATUSES: frozenset[QueuedJobStatus] = frozenset(
    {QueuedJobStatus.DEAD, QueuedJobStatus.DISCARDED}
)


class RetryQueuedJobUseCase(UseCaseContract[AdminJobCommand, AdminJobActionResult]):
    """
    A platform admin sends a dead (or discarded) job back to the queue: it
    runs again at once with a fresh set of attempts, its last error kept
    until the next attempt. Written to the audit log (UPDATE of the
    queued job, in the job's business log when it has a business).

    Raises:
        AccessDeniedError: the user is not a platform admin.
        NotFoundError: there is no such job.
        ConflictError: the job is waiting, running or done.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        job_repo: QueuedJobRepoContract,
        audit_log_repo: AuditLogRepoContract,
        job_wakeup: JobWakeupContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._job_repo: QueuedJobRepoContract = job_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._job_wakeup: JobWakeupContract = job_wakeup
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AdminJobCommand) -> AdminJobActionResult:
        admin: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_OPERATIONS,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()

        def send_back(job: QueuedJobDocument) -> None:
            if job.status not in RETRYABLE_STATUSES:
                raise ConflictError(
                    f"Job {job.id} is {job.status.value}; only dead or discarded "
                    "jobs can be retried."
                )

            job.status = QueuedJobStatus.PENDING
            job.attempts = JobAttemptCount(0)
            job.run_at = now
            job.lease_until = None
            job.lease_token = None
            job.updated_at = now

        retried: QueuedJobDocument = self._job_repo.update(input_data.job_id, send_back)
        entry: AuditLogEntryDocument = build_job_audit_entry(
            admin.id,
            retried,
            AuditAction.UPDATE,
            input_data.client_ip_address,
            now,
        )
        self._audit_log_repo.append(entry)
        self._job_wakeup.notify(retried.lane)
        return AdminJobActionResult(
            job=build_queued_job_view(retried),
            audit_log_entry_id=entry.id,
        )
