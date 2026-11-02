"""
Team invitations of accounts that never signed in lapse after seven days
(AUTHZ-09): a person who first signs in later is not in the team (a
recycled phone number lands nowhere), the removal is audited, and the
owner may invite them again. Accounts that already signed in join at once
and stay, as before.
"""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.businesses import BusinessQuery, InviteStaffRequest
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId
from tests.businesses.team_steps import invite, remove
from tests.users.accounts_phones import GEORGIA_MOBILE, GERMANY_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed

DAY_SECONDS: int = 24 * 60 * 60
INVITED: InviteStaffRequest = InviteStaffRequest(
    phone_number=RawPhoneNumberInput(GERMANY_MOBILE)
)


def with_invitation() -> tuple[AccountsTestbed, UserId, BusinessDocument]:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    invite(testbed, owner.user.id, business, INVITED)
    return testbed, owner.user.id, business


def members_of(testbed: AccountsTestbed, business: BusinessDocument) -> set[UserId]:
    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    return {member.user_id for member in stored.members}


def test_signing_in_within_seven_days_joins_the_team() -> None:
    testbed, _, business = with_invitation()
    testbed.clock.advance(7 * DAY_SECONDS - 60)

    staff = testbed.sign_in_with_phone(GERMANY_MOBILE)
    view = testbed.get_business.run(
        BusinessQuery(user_id=staff.user.id, business_id=business.id)
    )

    assert view.id == business.id
    assert staff.user.id in members_of(testbed, business)


def test_a_first_sign_in_after_seven_days_finds_no_team() -> None:
    testbed, owner_id, business = with_invitation()
    testbed.clock.advance(7 * DAY_SECONDS)

    late = testbed.sign_in_with_phone(GERMANY_MOBILE)

    with pytest.raises(NotFoundError):
        testbed.get_business.run(
            BusinessQuery(user_id=late.user.id, business_id=business.id)
        )
    assert testbed.list_my_businesses.run(late.user.id) == []
    assert members_of(testbed, business) == {owner_id}
    removals = [
        entry
        for entry in testbed.audit_log_repo.list_by_business(business.id)
        if entry.action is AuditAction.DELETE and entry.entity == "business_member"
    ]
    assert [(entry.actor_id, str(entry.entity_id)) for entry in removals] == [
        (late.user.id, str(late.user.id))
    ]


def test_the_owner_may_invite_again_once_it_lapsed() -> None:
    testbed, _, business = with_invitation()
    testbed.clock.advance(8 * DAY_SECONDS)
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    invite(testbed, owner.user.id, business, INVITED)
    testbed.clock.advance(DAY_SECONDS)
    staff = testbed.sign_in_with_phone(GERMANY_MOBILE)

    assert staff.user.id in members_of(testbed, business)
    assert len(members_of(testbed, business)) == 2


def test_a_pending_invitation_is_still_a_member_until_it_lapses() -> None:
    testbed, owner_id, business = with_invitation()
    testbed.clock.advance(DAY_SECONDS)

    with pytest.raises(ConflictError):
        invite(testbed, owner_id, business, INVITED)


def test_an_account_that_signed_in_before_stays_in_the_team() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    staff = testbed.sign_in_with_phone(GERMANY_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    invite(testbed, owner.user.id, business, INVITED)
    testbed.clock.advance(30 * DAY_SECONDS)

    again = testbed.sign_in_with_phone(GERMANY_MOBILE)

    assert again.user.id == staff.user.id
    assert staff.user.id in members_of(testbed, business)


def test_a_business_never_loses_its_last_owner_to_a_lapse() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    invite(
        testbed,
        owner.user.id,
        business,
        InviteStaffRequest(
            phone_number=RawPhoneNumberInput(GERMANY_MOBILE),
            role=BusinessMemberRole.OWNER,
        ),
    )
    remove(testbed, owner.user.id, business, owner.user.id)
    testbed.clock.advance(8 * DAY_SECONDS)

    heir = testbed.sign_in_with_phone(GERMANY_MOBILE)

    assert members_of(testbed, business) == {heir.user.id}
