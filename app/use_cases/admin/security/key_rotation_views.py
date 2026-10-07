"""The admin's view of a re-encryption run and the audit entry of starting one."""

from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.key_rotations import KeyRotationDocument
from app.schemas.dto.key_rotation import KeyRotationView
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.users.prefixed_id import UserId

ROTATE_ENCRYPTED_SECRETS_JOB: JobName = JobName("rotate_encrypted_secrets")
# One run at a time, whoever asks for it.
ROTATION_SERIAL_KEY: JobSerialKey = JobSerialKey("key_rotation:platform")
ENCRYPTION_KEYS_AUDIT_ENTITY: AuditEntityName = AuditEntityName("encryption_keys")


def build_key_rotation_view(rotation: KeyRotationDocument) -> KeyRotationView:
    return KeyRotationView(
        id=rotation.id,
        status=rotation.status,
        key_count=rotation.key_count,
        secrets_total=rotation.secrets_total,
        secrets_current=rotation.secrets_current,
        secrets_rotated=rotation.secrets_rotated,
        secrets_unreadable=rotation.secrets_unreadable,
        webhooks_renewed=rotation.webhooks_renewed,
        webhooks_failed=rotation.webhooks_failed,
        requested_at=rotation.created_at,
        started_at=rotation.started_at,
        finished_at=rotation.finished_at,
        last_error=rotation.last_error,
    )


def build_rotation_audit_entry(
    admin_id: UserId,
    rotation: KeyRotationDocument,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> AuditLogEntryDocument:
    """A platform admin had every stored secret sealed again (UPDATE)."""

    return AuditLogEntryDocument(
        business_id=None,
        actor_id=admin_id,
        action=AuditAction.UPDATE,
        entity=ENCRYPTION_KEYS_AUDIT_ENTITY,
        entity_id=AuditEntityReference(str(rotation.id)),
        ip_address=client_ip_address,
        created_at=now,
        updated_at=now,
    )
