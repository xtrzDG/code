"""Who sees and manages the team, and removing members."""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessMember
from app.schemas.dto.businesses import BusinessQuery, InviteStaffRequest
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId
from tests.businesses.team_steps import invite, remove
from tests.users.accounts_phones import (
    BRAZIL_MOBILE,
    GEORGIA_MOBILE,
    GERMANY_MOBILE,
    ISRAEL_MOBILE,
)
from tests.users.accounts_testbed import build_accounts_testbed


def test_staff_sees_the_business_but_cannot_manage_the_team() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    invite(
        testbed,
        owner.user.id,
        business,
        InviteStaffRequest(phone_number=RawPhoneNumberInput(GERMANY_MOBILE)),
    )
    staff = testbed.sign_in_with_phone(GERMANY_MOBILE)

    staff_view = testbed.get_business.run(
        BusinessQuery(user_id=staff.user.id, business_id=business.id)
    )
    staff_businesses = testbed.list_my_businesses.run(staff.user.id)

    assert staff_view.viewer_role is BusinessMemberRole.STAFF
    assert [view.id for view in staff_businesses] == [business.id]
    with pytest.raises(AccessDeniedError):
        invite(
            testbed,
            staff.user.id,
            business,
            InviteStaffRequest(phone_number=RawPhoneNumberInput(ISRAEL_MOBILE)),
        )
    with pytest.raises(AccessDeniedError):
        remove(testbed, staff.user.id, business, owner.user.id)


def test_strangers_cannot_see_or_change_a_business() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    stranger = testbed.sign_in_with_phone(ISRAEL_MOBILE)
    business = testbed.create_restaurant(owner.user.id)

    with pytest.raises(NotFoundError):
        testbed.get_business.run(
            BusinessQuery(user_id=stranger.user.id, business_id=business.id)
        )
    with pytest.raises(NotFoundError):
        invite(
            testbed,
            stranger.user.id,
            business,
            InviteStaffRequest(phone_number=RawPhoneNumberInput(BRAZIL_MOBILE)),
        )
    assert testbed.list_my_businesses.run(stranger.user.id) == []


def test_owner_removes_staff_and_the_removal_is_audited() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    view = invite(
        testbed,
        owner.user.id,
        business,
        InviteStaffRequest(phone_number=RawPhoneNumberInput(ISRAEL_MOBILE)),
    )
    staff_id = view.members[1].user_id

    after_removal = remove(testbed, owner.user.id, business, staff_id)

    assert [member.user_id for member in after_removal.members] == [owner.user.id]
    assert [
        (entry.action, entry.entity_id)
        for entry in testbed.audit_log_repo.list_by_business(business.id)
    ] == [
        (AuditAction.CREATE, str(staff_id)),
        (AuditAction.DELETE, str(staff_id)),
    ]
    assert testbed.list_my_businesses.run(staff_id) == []
    with pytest.raises(NotFoundError):
        remove(testbed, owner.user.id, business, staff_id)


def test_last_owner_cannot_be_removed_but_one_of_two_can_leave() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    co_owner = testbed.sign_in_with_phone(ISRAEL_MOBILE)
    business = testbed.create_restaurant(owner.user.id)

    with pytest.raises(ConflictError):
        remove(testbed, owner.user.id, business, owner.user.id)

    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    stored.members = [
        *stored.members,
        BusinessMember(user_id=co_owner.user.id, role=BusinessMemberRole.OWNER),
    ]
    testbed.business_repo.save(stored)

    after_leaving = remove(testbed, owner.user.id, business, owner.user.id)

    assert after_leaving.viewer_role is None
    assert [(member.user_id, member.role) for member in after_leaving.members] == [
        (co_owner.user.id, BusinessMemberRole.OWNER)
    ]
    with pytest.raises(ConflictError):
        remove(testbed, co_owner.user.id, business, co_owner.user.id)
    with pytest.raises(NotFoundError):
        testbed.get_business.run(
            BusinessQuery(user_id=owner.user.id, business_id=business.id)
        )


def test_member_without_a_user_record_is_still_listed() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    ghost_id = UserId()
    stored.members = [
        *stored.members,
        BusinessMember(user_id=ghost_id, role=BusinessMemberRole.STAFF),
    ]
    testbed.business_repo.save(stored)

    view = testbed.get_business.run(
        BusinessQuery(user_id=owner.user.id, business_id=business.id)
    )

    assert view.members[1].user_id == ghost_id
    assert view.members[1].phone_number is None
    assert view.members[1].is_verified is False
