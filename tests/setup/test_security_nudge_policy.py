"""
When the second-factor reminder shows (security_nudge_policy.py), and how
it becomes the owner's step of the guide (guide_steps.py).
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.security_nudges import SecurityNudgeReason
from app.schemas.constants.setup import SetupActionTarget, SetupStepCode
from app.schemas.domain.security_nudges import SecurityNudgeDocument
from app.schemas.dto.security_nudges import SecurityNudgeView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.security_nudges.constrained_integers import TeamMemberCount
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.security_nudge_identity import security_nudge_id_for
from app.utilities.security.security_nudge_policy import security_nudge_reason
from app.utilities.setup.guide_steps import protect_data_skips, protect_data_steps

BUSINESS_ID = BusinessId()
OWNER_ID = UserId()
DISMISSED_AT = Microseconds(1_790_000_000_000_000)


def dismissed(team_size: int) -> SecurityNudgeDocument:
    return SecurityNudgeDocument(
        id=security_nudge_id_for(BUSINESS_ID, OWNER_ID),
        business_id=BUSINESS_ID,
        user_id=OWNER_ID,
        dismissed_at=DISMISSED_AT,
        team_size_at_dismissal=TeamMemberCount(team_size),
    )


def reason(
    *,
    is_owner: bool = True,
    is_live: bool = True,
    has_second_factor: bool = False,
    team_size: int = 1,
    nudge: SecurityNudgeDocument | None = None,
) -> SecurityNudgeReason | None:
    return security_nudge_reason(
        is_owner=is_owner,
        is_live=is_live,
        has_second_factor=has_second_factor,
        team_size=TeamMemberCount(team_size),
        nudge=nudge,
    )


def test_a_live_owner_without_a_second_factor_is_reminded() -> None:
    assert reason() is SecurityNudgeReason.PROTECT_CUSTOMERS
    assert reason(team_size=4) is SecurityNudgeReason.PROTECT_CUSTOMERS


@pytest.mark.parametrize(
    ("is_owner", "is_live", "has_second_factor"),
    [(False, True, False), (True, False, False), (True, True, True)],
)
def test_staff_a_business_before_launch_and_a_second_factor_see_nothing(
    is_owner: bool, is_live: bool, has_second_factor: bool
) -> None:
    assert (
        reason(
            is_owner=is_owner,
            is_live=is_live,
            has_second_factor=has_second_factor,
            team_size=5,
        )
        is None
    )


def test_put_away_alone_it_comes_back_once_the_team_grows() -> None:
    assert reason(nudge=dismissed(1), team_size=1) is None
    assert reason(nudge=dismissed(1), team_size=2) is SecurityNudgeReason.TEAM_GREW
    assert reason(nudge=dismissed(0), team_size=3) is SecurityNudgeReason.TEAM_GREW


def test_put_away_with_a_team_it_stays_away() -> None:
    assert reason(nudge=dismissed(2), team_size=2) is None
    assert reason(nudge=dismissed(2), team_size=9) is None
    assert reason(nudge=dismissed(1), team_size=5, has_second_factor=True) is None


def test_one_reminder_per_person_and_business() -> None:
    other_owner = UserId()

    assert security_nudge_id_for(BUSINESS_ID, OWNER_ID) == security_nudge_id_for(
        BUSINESS_ID, OWNER_ID
    )
    assert security_nudge_id_for(BUSINESS_ID, OWNER_ID) != security_nudge_id_for(
        BUSINESS_ID, other_owner
    )
    assert security_nudge_id_for(BUSINESS_ID, OWNER_ID) != security_nudge_id_for(
        BusinessId(), OWNER_ID
    )


def view(
    *,
    is_owner: bool = True,
    has_second_factor: bool = False,
    reason: SecurityNudgeReason | None = SecurityNudgeReason.PROTECT_CUSTOMERS,
    dismissed_at: Microseconds | None = None,
) -> SecurityNudgeView:
    return SecurityNudgeView(
        is_shown=reason is not None,
        reason=reason,
        is_owner=is_owner,
        has_second_factor=has_second_factor,
        team_size=TeamMemberCount(1),
        dismissed_at=dismissed_at,
    )


def test_the_owner_has_a_protect_data_step_that_opens_account_security() -> None:
    (step,) = protect_data_steps(view())

    assert step.code is SetupStepCode.PROTECT_DATA
    assert step.target is SetupActionTarget.ACCOUNT_SECURITY
    assert step.is_done is False
    assert step.is_required is False
    assert protect_data_steps(view(has_second_factor=True, reason=None))[0].is_done
    assert protect_data_steps(view(is_owner=False, reason=None)) == []


def test_the_step_is_skipped_while_the_reminder_is_put_away() -> None:
    put_away = view(reason=None, dismissed_at=DISMISSED_AT)
    back = view(reason=SecurityNudgeReason.TEAM_GREW, dismissed_at=DISMISSED_AT)

    assert protect_data_skips(view()) == frozenset()
    assert protect_data_skips(put_away) == frozenset({SetupStepCode.PROTECT_DATA})
    assert protect_data_skips(back) == frozenset()
    assert protect_data_skips(view(is_owner=False, dismissed_at=DISMISSED_AT)) == (
        frozenset()
    )
