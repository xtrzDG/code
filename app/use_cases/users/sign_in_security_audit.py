"""
The security events of signing in and out, in the platform's audit chain
(they name no business):

- a wrong sign-in code is LOGIN_FAILED, and the one that used the code's
  last attempt OTP_LOCKED; the entry names the destination by its keyed
  digest (`login_destination_digests`), never the address, and the person
  when the address is theirs;
- a wrong second-factor code is LOGIN_FAILED, and the one that used the
  second step's last attempt MFA_LOCKED, about the person;
- signing out is LOGOUT (action `session_revoked`, the session ended).

Each rides on an action the previous release reads (`login`,
`session_revoked`); the platform alerts count the failed checks per
destination.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.compliance import AuditAction, AuditSecurityEvent
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.mfa.constrained_integers import MfaAttemptCount
from app.schemas.typings.users.constrained_integers import OtpAttemptCount
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.compliance.login_destination_digests import (
    derive_destination_key,
    login_destination_digest,
)

LOGIN_DESTINATION_ENTITY: AuditEntityName = AuditEntityName("login_destination")
USER_ENTITY: AuditEntityName = AuditEntityName("user")
USER_SESSION_ENTITY: AuditEntityName = AuditEntityName("user_session")


class SignInSecurityAudit:
    """Appends the security events of sign-in to the platform's chain."""

    def __init__(
        self,
        audit_log_repo: AuditLogRepoContract,
        user_repo: UserRepoContract,
        app_settings: AppSettings,
    ) -> None:
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._user_repo: UserRepoContract = user_repo
        self._destination_key: bytes = derive_destination_key(
            app_settings.encryption_key
        )

    def wrong_login_code(
        self,
        challenge: OtpChallengeDocument,
        attempt: OtpAttemptCount,
        max_attempts: OtpAttemptCount,
        client_ip_address: ClientIpAddress | None,
        now: Microseconds,
    ) -> None:
        """A wrong sign-in code; the one that locked the code says so."""

        owner: UserDocument | None = self._owner_of(challenge)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                actor_id=None if owner is None else owner.id,
                action=AuditAction.LOGIN,
                security_event=(
                    AuditSecurityEvent.OTP_LOCKED
                    if int(attempt) >= int(max_attempts)
                    else AuditSecurityEvent.LOGIN_FAILED
                ),
                entity=LOGIN_DESTINATION_ENTITY,
                entity_id=login_destination_digest(
                    self._destination_key,
                    challenge.login_method,
                    challenge.phone_number,
                    challenge.email,
                ),
                ip_address=client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )

    def wrong_second_factor(
        self,
        user_id: UserId,
        attempt: MfaAttemptCount,
        max_attempts: MfaAttemptCount,
        client_ip_address: ClientIpAddress | None,
        now: Microseconds,
    ) -> None:
        """A wrong authenticator or recovery code at sign-in."""

        self._audit_log_repo.append(
            AuditLogEntryDocument(
                actor_id=user_id,
                action=AuditAction.LOGIN,
                security_event=(
                    AuditSecurityEvent.MFA_LOCKED
                    if int(attempt) >= int(max_attempts)
                    else AuditSecurityEvent.LOGIN_FAILED
                ),
                entity=USER_ENTITY,
                entity_id=AuditEntityReference(str(user_id)),
                ip_address=client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )

    def _owner_of(self, challenge: OtpChallengeDocument) -> UserDocument | None:
        """The person whose phone or e-mail the code went to, if any."""

        if challenge.login_method is LoginMethod.PHONE:
            if challenge.phone_number is None:
                return None

            return self._user_repo.find_by_phone_number(challenge.phone_number)

        if challenge.email is None:
            return None

        return self._user_repo.find_by_email(challenge.email)


def signed_out_entry(
    session: UserSessionDocument,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> AuditLogEntryDocument:
    """The person signed out: the session behind the token ended."""

    return AuditLogEntryDocument(
        actor_id=session.user_id,
        action=AuditAction.SESSION_REVOKED,
        security_event=AuditSecurityEvent.LOGOUT,
        entity=USER_SESSION_ENTITY,
        entity_id=AuditEntityReference(str(session.id)),
        ip_address=client_ip_address,
        created_at=now,
        updated_at=now,
    )
