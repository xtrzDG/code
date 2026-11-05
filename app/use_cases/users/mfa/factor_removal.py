"""
What follows the removal of a second factor (the authenticator app or one
passkey). While the person keeps another one, nothing else changes.
Without one, their recovery codes go too and every session of theirs counts
as one factor again, so none keeps two-factor rights the person can no
longer prove. Either way the change is audited as MFA_CHANGED, with how many
sessions were lowered.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.mfa_repositories import RecoveryCodeRepoContract
from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.schemas.constants.users import SessionSweepReason
from app.schemas.dto.sessions import SessionSweep
from app.schemas.typings.compliance.strings import AuditEntityName, ClientIpAddress
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.session_sweeps import lower_sessions
from app.use_cases.users.mfa.mfa_records import audit_mfa_change


def settle_factor_removal(
    *,
    recovery_code_repo: RecoveryCodeRepoContract,
    user_session_repo: UserSessionRepoContract,
    audit_log_repo: AuditLogRepoContract,
    user_id: UserId,
    entity: AuditEntityName,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
    has_factor_left: bool,
) -> None:
    lowered: DocumentCount | None = None
    if not has_factor_left:
        recovery_code_repo.delete_for_user(user_id)
        lowered = lower_sessions(
            user_session_repo,
            SessionSweep(
                user_id=user_id,
                actor_id=user_id,
                reason=SessionSweepReason.AUTHENTICATOR_REMOVED,
                client_ip_address=client_ip_address,
                now=now,
            ),
        )
    audit_mfa_change(audit_log_repo, user_id, entity, client_ip_address, now, lowered)
