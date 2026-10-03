"""
Platform admin: the background job queue and its dead letters.

The admin sees what each job is, where it stands and why it failed, but
never its payload (it can hold customer data); retrying or discarding a
job is written to the audit log.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.prefixed_id import AuditLogEntryId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.constrained_integers import JobAttemptCount
from app.schemas.typings.platform.constrained_strings import JobName, PageCursor
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobErrorText
from app.schemas.typings.users.prefixed_id import UserId


class AdminJobsQuery(ImmutableDTO):
    """GET /v1/admin/jobs: one page, optionally of one status and job name."""

    user_id: UserId
    page: PageRequest
    status: QueuedJobStatus | None = None
    name: JobName | None = None


class QueuedJobView(ImmutableDTO):
    """
    One queued job as the platform admin sees it (no payload).

    `lease_until` is set while a worker runs the job; `last_error` is the
    error of the latest failed attempt.
    """

    id: QueuedJobId
    name: JobName
    lane: JobLane
    business_id: BusinessId | None = None
    status: QueuedJobStatus
    attempts: JobAttemptCount
    run_at: Microseconds
    lease_until: Microseconds | None = None
    last_error: JobErrorText | None = None
    created_at: Microseconds
    updated_at: Microseconds


class QueuedJobPage(ImmutableDTO):
    """Queued jobs, the most recently changed first."""

    items: list[QueuedJobView]
    next_cursor: PageCursor | None = None


class AdminJobCommand(ImmutableDTO):
    """POST /v1/admin/jobs/{job_id}/retry or …/discard by a platform admin."""

    user_id: UserId
    job_id: QueuedJobId
    client_ip_address: ClientIpAddress | None = None


class AdminJobActionResult(ImmutableDTO):
    """The job after a retry or discard, and the audit entry that records it."""

    job: QueuedJobView
    audit_log_entry_id: AuditLogEntryId
