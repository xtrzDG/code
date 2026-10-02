"""Two businesses sharing a visitor, with records in both, for data rights tests."""

from dataclasses import dataclass

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.businesses import InviteStaffCommand, InviteStaffRequest
from app.schemas.dto.compliance import ContactDataCommand
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId
from tests.compliance.visitor_records import SeededVisitor, seed_visitor
from tests.users.accounts_phones import GEORGIA_MOBILE, GERMANY_MOBILE, ISRAEL_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed


@dataclass(frozen=True)
class TwoTenants:
    testbed: AccountsTestbed
    owner_id: UserId
    staff_id: UserId
    business: BusinessDocument
    visitor: SeededVisitor
    neighbour: SeededVisitor
    foreign_visitor: SeededVisitor


def seed_two_tenants() -> TwoTenants:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    staff = testbed.sign_in_with_phone(GERMANY_MOBILE)
    other_owner = testbed.sign_in_with_phone(ISRAEL_MOBILE)
    business = testbed.create_restaurant(owner.user.id, "Sakhli")
    other_business = testbed.create_restaurant(other_owner.user.id, "Shuk")
    testbed.invite_staff.run(
        InviteStaffCommand(
            user_id=owner.user.id,
            business_id=business.id,
            invitation=InviteStaffRequest(
                phone_number=RawPhoneNumberInput(GERMANY_MOBILE)
            ),
        )
    )
    return TwoTenants(
        testbed=testbed,
        owner_id=owner.user.id,
        staff_id=staff.user.id,
        business=business,
        visitor=seed_visitor(
            testbed, business, "Giorgi", "+995577123456", "4242", "ka"
        ),
        neighbour=seed_visitor(
            testbed, business, "Nino", "+995577654321", "5353", "ru"
        ),
        foreign_visitor=seed_visitor(
            testbed, other_business, "Noa", "+972502223344", "6464", "he"
        ),
    )


def command(
    tenants: TwoTenants,
    contact_id: ContactId,
    user_id: UserId | None = None,
) -> ContactDataCommand:
    return ContactDataCommand(
        user_id=tenants.owner_id if user_id is None else user_id,
        business_id=tenants.business.id,
        contact_id=contact_id,
        client_ip_address=ClientIpAddress("192.0.2.10"),
    )
