"""
A business's rule that its team signs in with two factors
(`BusinessDocument.require_mfa_for_members`), for every check that acts on
businesses: the business access check, and the brand actions that reach
several locations at once (shared answers, the brand's team, its
locations). A brand owner acts as an owner in every location of the
brand, so each location's rule applies to what they do through the brand.
"""

from collections.abc import Iterable

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.two_factor_policy import (
    is_two_factor_session,
    mfa_required,
)

TEAM_TWO_FACTOR_MESSAGE: str = (
    "This business asks its team to sign in with two factors: add a passkey "
    "or an authenticator app (Account → Security) and sign in again."
)
BRAND_TWO_FACTOR_MESSAGE: str = (
    "A location of this brand asks its team to sign in with two factors: add "
    "a passkey or an authenticator app (Account → Security) and sign in again."
)


def is_one_factor_session(assurance: SessionAssurance | None, user_id: UserId) -> bool:
    """
    The request's session was signed in with the login code alone (or is
    not this person's). Work in the background (no session bound) acts on
    what a request already authorized, so it is not one.
    """

    return assurance is not None and not is_two_factor_session(assurance, user_id)


def require_team_two_factors(
    assurance: SessionAssurance | None,
    user_id: UserId,
    businesses: Iterable[BusinessDocument],
    message: str = TEAM_TWO_FACTOR_MESSAGE,
) -> None:
    """
    Raises:
        MfaRequiredError: one of `businesses` requires two factors of its
            team and the session was signed in with the login code alone
            (HTTP 403, reason `mfa_required`).
    """

    if not is_one_factor_session(assurance, user_id):
        return

    if any(business.require_mfa_for_members for business in businesses):
        raise mfa_required(message)
