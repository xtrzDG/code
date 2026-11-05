"""
The two-factor rule of a business's team as the brand checks apply it
(app/use_cases/shared/team_two_factor.py): a session signed in with the
login code alone is refused when any of the businesses requires two
factors; a two-factor session, and work in the background, pass.
"""

import pytest

from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.exceptions.mfa_errors import MfaRequiredError
from app.schemas.typings.users.prefixed_id import UserId, UserSessionId
from app.use_cases.shared.team_two_factor import (
    is_one_factor_session,
    require_team_two_factors,
)
from tests.brands.brand_builders import build_location

OWNER = UserId()


def session_of(user_id: UserId, auth_level: AuthLevel) -> SessionAssurance:
    return SessionAssurance(
        user_id=user_id, session_id=UserSessionId(), auth_level=auth_level
    )


def location(requires_two_factors: bool) -> BusinessDocument:
    return build_location(None, OWNER).model_copy(
        update={"require_mfa_for_members": requires_two_factors}
    )


def test_a_one_factor_session_is_refused_where_any_location_requires_two() -> None:
    one_factor = session_of(OWNER, AuthLevel.ONE_FACTOR)

    with pytest.raises(MfaRequiredError) as refused:
        require_team_two_factors(one_factor, OWNER, [location(False), location(True)])

    assert [reason.code for reason in refused.value.reasons] == ["mfa_required"]
    require_team_two_factors(one_factor, OWNER, [location(False), location(False)])


def test_two_factors_and_background_work_pass() -> None:
    both = [location(True), location(True)]

    require_team_two_factors(session_of(OWNER, AuthLevel.TWO_FACTOR), OWNER, both)
    require_team_two_factors(None, OWNER, both)

    assert is_one_factor_session(None, OWNER) is False


def test_another_person_s_two_factor_session_counts_as_one_factor() -> None:
    elsewhere = session_of(UserId(), AuthLevel.TWO_FACTOR)

    assert is_one_factor_session(elsewhere, OWNER) is True
    with pytest.raises(MfaRequiredError):
        require_team_two_factors(elsewhere, OWNER, [location(True)])
