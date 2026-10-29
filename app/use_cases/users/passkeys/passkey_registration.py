"""Adding a checked passkey, and what a person's first second factor brings."""

from typed_time_provider import Microseconds

from app.contracts.passkeys import PasskeyCeremonyAdapterContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.mfa_repositories import RecoveryCodeRepoContract
from app.contracts.repositories.passkey_repositories import PasskeyRepoContract
from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.schemas.constants.users import SessionSweepReason
from app.schemas.domain.passkeys import PasskeyChallengeDocument, PasskeyDocument
from app.schemas.dto.passkey_ceremonies import PasskeyRegistrationCredential
from app.schemas.dto.passkey_checks import CheckedRegistration
from app.schemas.dto.sessions import SessionSweep
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.mfa.constrained_strings import RecoveryCode
from app.schemas.typings.passkeys.constrained_strings import PasskeyName
from app.schemas.typings.users.constrained_strings import SessionUserAgent
from app.schemas.typings.users.prefixed_id import UserId, UserSessionId
from app.use_cases.shared.session_sweeps import end_sessions
from app.use_cases.users.mfa.mfa_records import issue_recovery_codes
from app.use_cases.users.passkeys.passkey_records import MAX_PASSKEYS_PER_USER
from app.utilities.security.passkey_identity import (
    default_passkey_name,
    passkey_id_for,
)

ALREADY_ADDED_MESSAGE: str = "This passkey is already added."
TOO_MANY_MESSAGE: str = (
    "This account keeps as many passkeys as it can. Remove one to add another."
)


def refuse_more_passkeys(passkey_repo: PasskeyRepoContract, user_id: UserId) -> None:
    """
    Raises:
        ConflictError: the person keeps the most passkeys one account may.
    """

    if int(passkey_repo.count_for_user(user_id)) >= MAX_PASSKEYS_PER_USER:
        raise ConflictError(TOO_MANY_MESSAGE)


def add_passkey(
    passkey_repo: PasskeyRepoContract,
    ceremony: PasskeyCeremonyAdapterContract,
    challenge: PasskeyChallengeDocument,
    credential: PasskeyRegistrationCredential,
    name: PasskeyName | None,
    user_agent: SessionUserAgent | None,
    now: Microseconds,
) -> PasskeyDocument:
    """
    Check the new passkey against the taken challenge and store it for the
    challenge's person, named after the browser and system that added it
    when the person gave no name.

    Raises:
        PasskeyRejectedError: the attestation does not check out.
        ConflictError: too many passkeys, or this credential is stored.
    """

    refuse_more_passkeys(passkey_repo, challenge.user_id)
    checked: CheckedRegistration = ceremony.check_registration(
        credential, challenge.challenge
    )
    passkey = PasskeyDocument(
        id=passkey_id_for(checked.credential_id),
        user_id=challenge.user_id,
        credential_id=checked.credential_id,
        public_key=checked.public_key,
        sign_count=checked.sign_count,
        transports=checked.transports,
        aaguid=checked.aaguid,
        name=name or default_passkey_name(user_agent),
        is_synced=checked.is_synced,
        is_backed_up=checked.is_backed_up,
        created_at=now,
        updated_at=now,
    )
    if not passkey_repo.add(passkey):
        raise ConflictError(ALREADY_ADDED_MESSAGE)

    return passkey


def start_second_factor(
    recovery_code_repo: RecoveryCodeRepoContract,
    user_session_repo: UserSessionRepoContract,
    audit_log_repo: AuditLogRepoContract,
    user_id: UserId,
    kept_session_id: UserSessionId | None,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> list[RecoveryCode]:
    """
    A person's first second factor: a new set of recovery codes (shown
    once) for the day the passkey is gone, and every other session ends,
    since each was signed in without it (SESSION_REVOKED with the count).
    """

    codes: list[RecoveryCode] = issue_recovery_codes(recovery_code_repo, user_id, now)
    end_sessions(
        user_session_repo,
        audit_log_repo,
        SessionSweep(
            user_id=user_id,
            actor_id=user_id,
            reason=SessionSweepReason.AUTHENTICATOR_ADDED,
            kept_session_id=kept_session_id,
            client_ip_address=client_ip_address,
            now=now,
        ),
    )
    return codes
