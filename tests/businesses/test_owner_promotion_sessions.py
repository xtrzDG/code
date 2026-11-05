"""
A member made an owner signs in again: every session of theirs ends once
the promotion is stored, audited in the platform's chain with the count;
a demotion, an unchanged role or a refused change ends nothing.
"""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.businesses import (
    ChangeMemberRoleCommand,
    InviteStaffRequest,
    MemberRoleChange,
)
from app.schemas.dto.users import LoginSessionView
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ConflictError,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId
from tests.businesses.team_steps import invite
from tests.users.access.session_steps import check
from tests.users.accounts_phones import GEORGIA_MOBILE, ISRAEL_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed

OWNER_IP: str = "198.51.100.4"
RESEND_WAIT_SECONDS: int = 31


def team_with_staff() -> tuple[
    AccountsTestbed, BusinessDocument, LoginSessionView, LoginSessionView
]:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    invite(
        testbed,
        owner.user.id,
        business,
        InviteStaffRequest(phone_number=RawPhoneNumberInput(ISRAEL_MOBILE)),
    )
    staff = testbed.sign_in_with_phone(ISRAEL_MOBILE)
    return testbed, business, owner, staff


def change_role(
    testbed: AccountsTestbed,
    actor_id: UserId,
    business: BusinessDocument,
    member_id: UserId,
    role: BusinessMemberRole,
) -> None:
    testbed.change_member_role.run(
        ChangeMemberRoleCommand(
            user_id=actor_id,
            business_id=business.id,
            member_user_id=member_id,
            change=MemberRoleChange(role=role),
            client_ip_address=ClientIpAddress(OWNER_IP),
        )
    )


def swept(testbed: AccountsTestbed) -> list[str]:
    return [
        " ".join(
            str(part)
            for part in (
                entry.entity_id,
                int(entry.record_count or 0),
                entry.actor_id,
                entry.business_id,
            )
        )
        for entry in testbed.audit_log_collection.list_all()
        if entry.action is AuditAction.SESSION_REVOKED
    ]


def test_a_member_made_owner_signs_in_again() -> None:
    testbed, business, owner, staff = team_with_staff()
    testbed.clock.advance(RESEND_WAIT_SECONDS)
    second_device = testbed.sign_in_with_phone(ISRAEL_MOBILE)

    change_role(
        testbed, owner.user.id, business, staff.user.id, BusinessMemberRole.OWNER
    )

    for session in (staff, second_device):
        with pytest.raises(AuthenticationRequiredError):
            testbed.authenticate_user.run(check(session))
    # The owner who promoted keeps their own session.
    assert testbed.authenticate_user.run(check(owner)).user_id == owner.user.id
    assert swept(testbed) == [
        f"{staff.user.id}:business_role_raised 2 {owner.user.id} None"
    ]
    [entry] = [
        entry
        for entry in testbed.audit_log_collection.list_all()
        if entry.action is AuditAction.SESSION_REVOKED
    ]
    assert str(entry.ip_address) == OWNER_IP


def test_a_demotion_or_an_unchanged_role_ends_no_session() -> None:
    testbed, business, owner, staff = team_with_staff()
    change_role(
        testbed, owner.user.id, business, staff.user.id, BusinessMemberRole.OWNER
    )
    testbed.clock.advance(RESEND_WAIT_SECONDS)
    again = testbed.sign_in_with_phone(ISRAEL_MOBILE)

    change_role(
        testbed, owner.user.id, business, staff.user.id, BusinessMemberRole.OWNER
    )
    change_role(
        testbed, owner.user.id, business, staff.user.id, BusinessMemberRole.STAFF
    )

    assert testbed.authenticate_user.run(check(again)).user_id == staff.user.id
    assert len(swept(testbed)) == 1


def test_a_refused_change_ends_no_session() -> None:
    testbed, business, owner, staff = team_with_staff()

    with pytest.raises(ConflictError):
        change_role(
            testbed, owner.user.id, business, owner.user.id, BusinessMemberRole.STAFF
        )

    assert testbed.authenticate_user.run(check(staff)).user_id == staff.user.id
    assert testbed.authenticate_user.run(check(owner)).user_id == owner.user.id
    assert swept(testbed) == []
