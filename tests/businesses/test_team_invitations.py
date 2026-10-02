"""Inviting staff by phone number or email, and invitations that add nobody."""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.dto.businesses import InviteStaffRequest
from app.schemas.exceptions.application_errors import (
    ConflictError,
    InvalidPhoneNumberError,
    ValidationFailedError,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.strings import RawEmailAddressInput, UserDisplayName
from tests.businesses.team_steps import invite
from tests.users.accounts_phones import BRAZIL_MOBILE, GEORGIA_MOBILE, ISRAEL_MOBILE
from tests.users.accounts_testbed import build_accounts_testbed


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
