"""Co-owners and member roles: promoting, demoting and the last owner."""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.businesses import (
    BusinessView,
    ChangeMemberRoleCommand,
    InviteStaffRequest,
    MemberRoleChange,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import RawEmailAddressInput
from tests.businesses.team_steps import invite
from tests.users.accounts_phones import GEORGIA_MOBILE, ISRAEL_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed


def change_role(
    testbed: AccountsTestbed,
    actor_id: UserId,
    business: BusinessDocument,
    member_id: UserId,
    role: BusinessMemberRole,
) -> BusinessView:
    return testbed.change_member_role.run(
        ChangeMemberRoleCommand(
            user_id=actor_id,
            business_id=business.id,
            member_user_id=member_id,
            change=MemberRoleChange(role=role),
            client_ip_address=ClientIpAddress("198.51.100.4"),
        )
    )


def test_owner_invites_a_co_owner_who_may_manage_the_team() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)

    view = invite(
        testbed,
        owner.user.id,
        business,
        InviteStaffRequest(
            email=RawEmailAddressInput("partner@example.com"),
            role=BusinessMemberRole.OWNER,
        ),
    )
    co_owner_id = view.members[1].user_id

    assert view.members[1].role is BusinessMemberRole.OWNER
    after = invite(
        testbed,
        co_owner_id,
        business,
        InviteStaffRequest(email=RawEmailAddressInput("cook@example.com")),
    )
    assert [member.role for member in after.members] == [
        BusinessMemberRole.OWNER,
        BusinessMemberRole.OWNER,
        BusinessMemberRole.STAFF,
    ]


def test_owner_promotes_and_demotes_a_member_and_each_change_is_audited() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    staff_id = (
        invite(
            testbed,
            owner.user.id,
            business,
            InviteStaffRequest(phone_number=RawPhoneNumberInput(ISRAEL_MOBILE)),
        )
        .members[1]
        .user_id
    )

    promoted = change_role(
        testbed, owner.user.id, business, staff_id, BusinessMemberRole.OWNER
    )
    unchanged = change_role(
        testbed, owner.user.id, business, staff_id, BusinessMemberRole.OWNER
    )
    demoted_self = change_role(
        testbed, owner.user.id, business, owner.user.id, BusinessMemberRole.STAFF
    )

    assert promoted.members[1].role is BusinessMemberRole.OWNER
    assert unchanged.members[1].role is BusinessMemberRole.OWNER
    assert demoted_self.viewer_role is BusinessMemberRole.STAFF
    entries = testbed.audit_log_repo.list_by_business(business.id)
    assert [(entry.action, entry.entity_id) for entry in entries] == [
        (AuditAction.CREATE, str(staff_id)),
        (AuditAction.UPDATE, str(staff_id)),
        (AuditAction.UPDATE, str(owner.user.id)),
    ]
    assert str(entries[1].ip_address) == "198.51.100.4"
    with pytest.raises(AccessDeniedError):
        change_role(
            testbed, owner.user.id, business, staff_id, BusinessMemberRole.STAFF
        )


def test_the_last_owner_can_never_be_made_staff() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)

    with pytest.raises(ConflictError):
        change_role(
            testbed, owner.user.id, business, owner.user.id, BusinessMemberRole.STAFF
        )

    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    assert [member.role for member in stored.members] == [BusinessMemberRole.OWNER]
    assert testbed.audit_log_repo.list_by_business(business.id) == []


def test_role_changes_need_an_owner_and_a_member() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    staff_id = (
        invite(
            testbed,
            owner.user.id,
            business,
            InviteStaffRequest(phone_number=RawPhoneNumberInput(ISRAEL_MOBILE)),
        )
        .members[1]
        .user_id
    )

    with pytest.raises(AccessDeniedError):
        change_role(testbed, staff_id, business, staff_id, BusinessMemberRole.OWNER)
    with pytest.raises(NotFoundError):
        change_role(
            testbed, owner.user.id, business, UserId(), BusinessMemberRole.OWNER
        )
