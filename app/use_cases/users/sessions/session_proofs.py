"""
Recording on the request's session that its person just proved it is them
(a step-up, a new authenticator or a first passkey).

A proof that keeps the session's level, or lowers it, is written on the
session. A proof that raises a one-factor session to two factors is not:
the session stays what it was and keeps the hash of a one-time rotation
ticket, which goes to the client that made the proof alone. With it, that
client swaps the token (RotateSessionUseCase), and only the new token
carries the two factors and the proof; a copy of the old token, taken
before or after, never does.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.users import UserSessionDocument
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.sessions import SessionProof
from app.schemas.typings.users.constrained_strings import SessionRotationTicket
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.session_rotation_tickets import (
    generate_rotation_ticket,
    hash_rotation_ticket,
    ticket_expiry,
)


def record_proof(
    session_assurance: SessionAssuranceContract,
    user_session_repo: UserSessionRepoContract,
    user_id: UserId,
    auth_level: AuthLevel,
    proven_at: Microseconds,
) -> SessionProof:
    """
    The proof of `user_id` made at `proven_at` with `auth_level`, on the
    request's session when it is theirs (nothing otherwise).
    """

    assurance: SessionAssurance | None = session_assurance.current()
    if assurance is None or assurance.user_id != user_id:
        return SessionProof()

    if raises_level(assurance, auth_level):
        ticket: SessionRotationTicket = generate_rotation_ticket()
        held: UserSessionDocument | None = user_session_repo.hold_rotation_ticket(
            assurance.session_id,
            hash_rotation_ticket(ticket),
            proven_at,
            ticket_expiry(proven_at),
        )
        return SessionProof() if held is None else SessionProof(rotation_ticket=ticket)

    recorded: UserSessionDocument | None = user_session_repo.record_authentication(
        assurance.session_id, auth_level, proven_at
    )
    return SessionProof(is_recorded=recorded is not None)


def raises_level(assurance: SessionAssurance, auth_level: AuthLevel) -> bool:
    """A proof with two factors on a session that counts as one."""

    return (
        auth_level is AuthLevel.TWO_FACTOR
        and assurance.auth_level is not AuthLevel.TWO_FACTOR
    )
