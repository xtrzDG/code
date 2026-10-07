"""Recording on the current session that its person changed two-factor sign-in."""

from typed_time_provider import Microseconds

from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.schemas.constants.mfa import AuthLevel
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.typings.users.prefixed_id import UserId


def record_session_level(
    session_assurance: SessionAssuranceContract,
    user_session_repo: UserSessionRepoContract,
    user_id: UserId,
    auth_level: AuthLevel,
    authenticated_at: Microseconds | None,
) -> None:
    """
    Store how the request's session counts from now on, when it is this
    user's: two factors once their authenticator's first code matched, one
    factor once it is removed. `authenticated_at` None keeps the stored one.
    """

    assurance: SessionAssurance | None = session_assurance.current()
    if assurance is None or assurance.user_id != user_id:
        return

    user_session_repo.record_authentication(
        assurance.session_id,
        auth_level,
        authenticated_at
        if authenticated_at is not None
        else assurance.authenticated_at or Microseconds(0),
    )
