"""
An existing account invited straight in as an owner (it joins at once)
signs in again like a member made owner; invited as staff, or refused as
an existing member, it keeps its sessions. The sweep of a promotion or an
owner invitation is retry-safe: a sweep that fails stores nothing, and the
retry sweeps again.
"""

from collections.abc import Callable

import pytest

from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.businesses import InviteStaffRequest
from app.schemas.dto.users import LoginSessionView
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ConflictError,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.users.prefixed_id import UserId, UserSessionId
from tests.businesses.team_steps import invite
from tests.businesses.test_owner_promotion_sessions import (
    change_role,
    swept,
    team_with_staff,
)
from tests.users.access.session_steps import check
from tests.users.accounts_phones import GEORGIA_MOBILE, ISRAEL_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed


class SweepFailure(RuntimeError):
    """The session store failing once in the middle of a sweep."""


def owner_with_business() -> tuple[AccountsTestbed, BusinessDocument, LoginSessionView]:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    return testbed, testbed.create_restaurant(owner.user.id), owner


def as_owner(phone: str) -> InviteStaffRequest:
    return InviteStaffRequest(
        phone_number=RawPhoneNumberInput(phone), role=BusinessMemberRole.OWNER
    )


def failing_once(testbed: AccountsTestbed, monkeypatch: pytest.MonkeyPatch) -> None:
    """The next sweep of the session store fails; the ones after work."""

    working: Callable[[UserId, UserSessionId | None], DocumentCount] = (
        testbed.user_session_repo.delete_for_user
    )
    calls: list[UserId] = []

    def delete_for_user(
        user_id: UserId, except_session_id: UserSessionId | None = None
    ) -> DocumentCount:
        calls.append(user_id)
        if len(calls) == 1:
            raise SweepFailure("the session store is unavailable")
        return working(user_id, except_session_id)

    monkeypatch.setattr(testbed.user_session_repo, "delete_for_user", delete_for_user)


def role_of(
    testbed: AccountsTestbed, business: BusinessDocument, user_id: UserId
) -> BusinessMemberRole | None:
    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    return next(
        (member.role for member in stored.members if member.user_id == user_id), None
    )


def test_an_existing_account_invited_as_owner_signs_in_again() -> None:
    testbed, business, owner = owner_with_business()
    invited = testbed.sign_in_with_phone(ISRAEL_MOBILE)

    invite(testbed, owner.user.id, business, as_owner(ISRAEL_MOBILE))

    with pytest.raises(AuthenticationRequiredError):
        testbed.authenticate_user.run(check(invited))
    assert testbed.authenticate_user.run(check(owner)).user_id == owner.user.id
    assert role_of(testbed, business, invited.user.id) is BusinessMemberRole.OWNER
    assert swept(testbed) == [
        f"{invited.user.id}:business_role_raised 1 {owner.user.id} None"
    ]


def test_an_account_invited_as_staff_or_refused_keeps_its_sessions() -> None:
    testbed, business, owner = owner_with_business()
    invited = testbed.sign_in_with_phone(ISRAEL_MOBILE)
    invite(
        testbed,
        owner.user.id,
        business,
        InviteStaffRequest(phone_number=RawPhoneNumberInput(ISRAEL_MOBILE)),
    )

    with pytest.raises(ConflictError):
        invite(testbed, owner.user.id, business, as_owner(ISRAEL_MOBILE))

    assert testbed.authenticate_user.run(check(invited)).user_id == invited.user.id
    assert role_of(testbed, business, invited.user.id) is BusinessMemberRole.STAFF
    assert swept(testbed) == []


def test_a_retried_owner_invitation_sweeps_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    testbed, business, owner = owner_with_business()
    invited = testbed.sign_in_with_phone(ISRAEL_MOBILE)
    failing_once(testbed, monkeypatch)

    with pytest.raises(SweepFailure):
        invite(testbed, owner.user.id, business, as_owner(ISRAEL_MOBILE))
    # Nothing was stored: the account is no member yet and still signed in.
    assert role_of(testbed, business, invited.user.id) is None
    assert testbed.authenticate_user.run(check(invited)).user_id == invited.user.id
    invite(testbed, owner.user.id, business, as_owner(ISRAEL_MOBILE))

    with pytest.raises(AuthenticationRequiredError):
        testbed.authenticate_user.run(check(invited))
    assert role_of(testbed, business, invited.user.id) is BusinessMemberRole.OWNER


def test_a_retried_promotion_sweeps_again(monkeypatch: pytest.MonkeyPatch) -> None:
    testbed, business, owner, staff = team_with_staff()
    failing_once(testbed, monkeypatch)

    with pytest.raises(SweepFailure):
        change_role(
            testbed, owner.user.id, business, staff.user.id, BusinessMemberRole.OWNER
        )
    assert role_of(testbed, business, staff.user.id) is BusinessMemberRole.STAFF
    assert testbed.authenticate_user.run(check(staff)).user_id == staff.user.id
    change_role(
        testbed, owner.user.id, business, staff.user.id, BusinessMemberRole.OWNER
    )

    with pytest.raises(AuthenticationRequiredError):
        testbed.authenticate_user.run(check(staff))
    assert role_of(testbed, business, staff.user.id) is BusinessMemberRole.OWNER
    assert swept(testbed) == [
        f"{staff.user.id}:business_role_raised 1 {owner.user.id} None"
    ]
