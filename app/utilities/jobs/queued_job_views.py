"""Queued jobs as the platform admin sees them (no payload), and their audit."""

from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.admin_jobs import QueuedJobView
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.users.prefixed_id import UserId

QUEUED_JOB_AUDIT_ENTITY: AuditEntityName = AuditEntityName("queued_job")


def build_queued_job_view(job: QueuedJobDocument) -> QueuedJobView:
    return QueuedJobView(
        id=job.id,
        name=job.name,
        lane=job.lane,
        business_id=job.business_id,
        status=job.status,
        attempts=job.attempts,
        run_at=job.run_at,
        lease_until=job.lease_until,
        last_error=job.last_error,
        dead_reason=job.dead_reason,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def build_job_audit_entry(
    admin_id: UserId,
    job: QueuedJobDocument,
    action: AuditAction,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> AuditLogEntryDocument:
    """
    The audit entry of a platform admin's retry (UPDATE) or discard (DELETE)
    of a queued job; in the job's business log when it has a business.
    """

    return AuditLogEntryDocument(
        business_id=job.business_id,
        actor_id=admin_id,
        action=action,
        entity=QUEUED_JOB_AUDIT_ENTITY,
        entity_id=AuditEntityReference(str(job.id)),
        ip_address=client_ip_address,
        created_at=now,
        updated_at=now,
    )
