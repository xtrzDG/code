"""A passkey as its person sees it, the account it is shown under, and its audit."""

from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.passkeys import PasskeyDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.passkeys import PasskeyView
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.passkeys.strings import PasskeyAccountName

PASSKEY_ENTITY: AuditEntityName = AuditEntityName("passkey")
# How many passkeys one person may keep: phones, laptops, a security key
# or two, with room to spare.
MAX_PASSKEYS_PER_USER: int = 10


def passkey_view(passkey: PasskeyDocument) -> PasskeyView:
    return PasskeyView(
        id=passkey.id,
        name=passkey.name,
        created_at=passkey.created_at,
        last_used_at=passkey.last_used_at,
        is_synced=passkey.is_synced,
        is_backed_up=passkey.is_backed_up,
        transports=list(passkey.transports),
        clone_suspected_at=passkey.clone_suspected_at,
    )


def account_name_of(user: UserDocument) -> PasskeyAccountName:
    """The e-mail address or phone number an authenticator shows with the passkey."""

    return PasskeyAccountName(str(user.email or user.phone_number or user.id))


def audit_passkey_suspended(
    audit_log_repo: AuditLogRepoContract,
    passkey: PasskeyDocument,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> None:
    """
    MFA_CHANGED: a passkey whose counter went backwards stopped signing (a
    copy of its authenticator was used). It names no business.
    """

    audit_log_repo.append(
        AuditLogEntryDocument(
            actor_id=passkey.user_id,
            action=AuditAction.MFA_CHANGED,
            entity=PASSKEY_ENTITY,
            entity_id=AuditEntityReference(f"{passkey.id}:clone_suspected"),
            ip_address=client_ip_address,
            created_at=now,
            updated_at=now,
        )
    )
