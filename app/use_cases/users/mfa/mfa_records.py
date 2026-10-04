"""Recovery code sets and the audit entries of two-factor changes."""

from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.mfa_repositories import RecoveryCodeRepoContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.mfa import RecoveryCodeDocument
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.mfa.constrained_strings import RecoveryCode
from app.schemas.typings.mfa.prefixed_id import RecoveryCodeId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.recovery_codes import (
    generate_recovery_codes,
    hash_recovery_code,
)

TOTP_FACTOR_ENTITY: AuditEntityName = AuditEntityName("totp_factor")
RECOVERY_CODES_ENTITY: AuditEntityName = AuditEntityName("recovery_codes")


def issue_recovery_codes(
    recovery_code_repo: RecoveryCodeRepoContract,
    user_id: UserId,
    now: Microseconds,
) -> list[RecoveryCode]:
    """A new set of codes replacing the old one; only their hashes are stored."""

    codes: list[RecoveryCode] = generate_recovery_codes()
    documents: list[RecoveryCodeDocument] = []
    for code in codes:
        code_id: RecoveryCodeId = RecoveryCodeId()
        documents.append(
            RecoveryCodeDocument(
                id=code_id,
                user_id=user_id,
                code_hash=hash_recovery_code(user_id, code_id, code),
                created_at=now,
                updated_at=now,
            )
        )
    recovery_code_repo.replace_for_user(user_id, documents)
    return codes


def audit_mfa_change(
    audit_log_repo: AuditLogRepoContract,
    user_id: UserId,
    entity: AuditEntityName,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> None:
    """MFA_CHANGED by the person themselves; it names no business."""

    audit_log_repo.append(
        AuditLogEntryDocument(
            actor_id=user_id,
            action=AuditAction.MFA_CHANGED,
            entity=entity,
            entity_id=AuditEntityReference(str(user_id)),
            ip_address=client_ip_address,
            created_at=now,
            updated_at=now,
        )
    )
