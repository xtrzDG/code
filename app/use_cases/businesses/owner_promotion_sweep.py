from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.storage import StorageScopeContract
from app.schemas.constants.users import SessionSweepReason
from app.schemas.dto.sessions import SessionSweep
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.session_sweeps import end_sessions


class OwnerPromotionSweep:
    """
    A member made an owner of a business signs in again: every session of
    theirs ends (`business_role_raised`, audited in the platform's chain as
    SESSION_REVOKED with the count, naming no business), so the owner's
    rights come only with a new sign-in and a new token, never on a token
    that may have been copied while they were staff. Sessions are platform
    rows the business's storage scope cannot write: the sweep runs
    platform-wide, for this one person only.
    """

    def __init__(
        self,
        user_session_repo: UserSessionRepoContract,
        audit_log_repo: AuditLogRepoContract,
        storage_scope: StorageScopeContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._storage_scope: StorageScopeContract = storage_scope
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def end_sessions_of(
        self,
        member_user_id: UserId,
        actor_id: UserId,
        client_ip_address: ClientIpAddress | None,
    ) -> DocumentCount:
        with self._storage_scope.platform_wide():
            return end_sessions(
                self._user_session_repo,
                self._audit_log_repo,
                SessionSweep(
                    user_id=member_user_id,
                    actor_id=actor_id,
                    reason=SessionSweepReason.BUSINESS_ROLE_RAISED,
                    client_ip_address=client_ip_address,
                    now=self._wall_clock.now_unix(),
                ),
            )
