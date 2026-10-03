"""A signed-in owner, a staff member and their business for compliance tests."""

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.businesses import InviteStaffCommand, InviteStaffRequest
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId
from tests.users.accounts_phones import GEORGIA_MOBILE, GERMANY_MOBILE
from tests.users.accounts_testbed import AccountsTestbed


def business_with_staff(
    testbed: AccountsTestbed,
) -> tuple[UserId, UserId, BusinessDocument]:
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    testbed.invite_staff.run(
        InviteStaffCommand(
            user_id=owner.user.id,
            business_id=business.id,
            invitation=InviteStaffRequest(
                phone_number=RawPhoneNumberInput(GERMANY_MOBILE)
            ),
        )
    )
    staff = testbed.sign_in_with_phone(GERMANY_MOBILE)
    return owner.user.id, staff.user.id, business
