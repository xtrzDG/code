import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.dto.businesses import (
    BusinessQuery,
    BusinessView,
    ChangeMemberRoleCommand,
    InviteStaffCommand,
    InviteStaffRequest,
    MemberRoleChange,
    RemoveMemberCommand,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    InvalidPhoneNumberError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import RawEmailAddressInput, UserDisplayName
from tests.users.accounts_phones import (
    BRAZIL_MOBILE,
    GEORGIA_MOBILE,
    GERMANY_MOBILE,
    ISRAEL_MOBILE,
)
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed


def invite(
    testbed: AccountsTestbed,
    owner_id: UserId,
    business: BusinessDocument,
    invitation: InviteStaffRequest,
) -> BusinessView:
    return testbed.invite_staff.run(
        InviteStaffCommand(
            user_id=owner_id,
            business_id=business.id,
            invitation=invitation,
            client_ip_address=ClientIpAddress("198.51.100.4"),
        )
    )


def remove(
    testbed: AccountsTestbed,
    actor_id: UserId,
    business: BusinessDocument,
    member_id: UserId,
) -> BusinessView:
    return testbed.remove_member.run(
        RemoveMemberCommand(
            user_id=actor_id,
            business_id=business.id,
            member_user_id=member_id,
        )
    )


def test_owner_invites_staff_with_a_phone_number_of_another_country() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)

    view = invite(
        testbed,
        owner.user.id,
        business,
        InviteStaffRequest(
            phone_number=RawPhoneNumberInput(ISRAEL_MOBILE),
            display_name=UserDisplayName("Tamar"),
        ),
    )

    staff_user = testbed.user_repo.find_by_phone_number(
        E164PhoneNumber("+972502345678")
    )
    assert staff_user is not None
    assert staff_user.is_verified is False
    assert staff_user.country_code == "IL"
    assert staff_user.locale == "ka"
    assert staff_user.login_method is LoginMethod.PHONE
    assert [(member.role, member.display_name) for member in view.members] == [
        (BusinessMemberRole.OWNER, None),
        (BusinessMemberRole.STAFF, "Tamar"),
    ]
    assert view.members[1].phone_number == "+972502345678"
    assert view.members[1].is_verified is False
    entries = testbed.audit_log_repo.list_by_business(business.id)
    assert [(entry.action, entry.entity, entry.entity_id) for entry in entries] == [
        (AuditAction.CREATE, "business_member", str(staff_user.id))
    ]
    assert entries[0].ip_address == "198.51.100.4"


def test_national_numbers_are_read_in_the_business_country_or_the_hint() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)

    invite(
        testbed,
        owner.user.id,
        business,
        InviteStaffRequest(phone_number=RawPhoneNumberInput("599 12 34 56")),
    )
    invite(
        testbed,
        owner.user.id,
        business,
        InviteStaffRequest(
            phone_number=RawPhoneNumberInput("(11) 96123-4567"),
            country_hint=CountryCode("BR"),
        ),
    )

    members = testbed.business_repo.get(business.id)
    assert members is not None
    phone_numbers = [
        user.phone_number
        for member in members.members
        if (user := testbed.user_repo.get(member.user_id)) is not None
    ]
    assert phone_numbers == ["+995555123456", "+995599123456", "+5511961234567"]


def test_owner_invites_staff_by_email_and_reuses_existing_accounts() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    existing_staff = testbed.sign_in_with_phone(BRAZIL_MOBILE)
    business = testbed.create_restaurant(owner.user.id)

    invite(
        testbed,
        owner.user.id,
        business,
        InviteStaffRequest(email=RawEmailAddressInput(" Chef@Example.com ")),
    )
    view = invite(
        testbed,
        owner.user.id,
        business,
        InviteStaffRequest(phone_number=RawPhoneNumberInput(BRAZIL_MOBILE)),
    )

    email_user = testbed.user_repo.find_by_email(EmailAddress("chef@example.com"))
    assert email_user is not None
    assert email_user.login_method is LoginMethod.EMAIL
    assert email_user.country_code is None
    assert [member.user_id for member in view.members][1:] == [
        email_user.id,
        existing_staff.user.id,
    ]
    reused_user = testbed.user_repo.get(existing_staff.user.id)
    assert reused_user is not None
    assert reused_user.is_verified is True


@pytest.mark.parametrize(
    ("invitation", "expected_error"),
    [
        (InviteStaffRequest(), ValidationFailedError),
        (
            InviteStaffRequest(
                phone_number=RawPhoneNumberInput(ISRAEL_MOBILE),
                email=RawEmailAddressInput("x@example.com"),
            ),
            ValidationFailedError,
        ),
        (
            InviteStaffRequest(phone_number=RawPhoneNumberInput("12")),
            InvalidPhoneNumberError,
        ),
        (
            InviteStaffRequest(email=RawEmailAddressInput("chef@")),
            ValidationFailedError,
        ),
        (
            InviteStaffRequest(
                phone_number=RawPhoneNumberInput(ISRAEL_MOBILE),
                display_name=UserDisplayName("x" * 101),
            ),
            ValidationFailedError,
        ),
    ],
)
def test_invalid_invitations_add_nobody(
    invitation: InviteStaffRequest,
    expected_error: type[Exception],
) -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)

    with pytest.raises(expected_error):
        invite(testbed, owner.user.id, business, invitation)

    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    assert len(stored.members) == 1


def test_inviting_a_member_twice_conflicts() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    staff_invitation = InviteStaffRequest(
        phone_number=RawPhoneNumberInput(ISRAEL_MOBILE)
    )
    invite(testbed, owner.user.id, business, staff_invitation)

    with pytest.raises(ConflictError):
        invite(testbed, owner.user.id, business, staff_invitation)
    with pytest.raises(ConflictError):
        invite(
            testbed,
            owner.user.id,
            business,
            InviteStaffRequest(phone_number=RawPhoneNumberInput("555 12 34 56")),
        )


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
