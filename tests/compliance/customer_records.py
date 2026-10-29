"""Customers with conversations, bookings and leads for the contacts tests."""

from dataclasses import dataclass

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.businesses import InviteStaffCommand, InviteStaffRequest
from app.schemas.dto.contacts import ContactListQuery, ContactPage
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.constrained_strings import ContactSearchText
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId
from tests.compliance.visitor_records import SeededVisitor, seed_visitor
from tests.users.accounts_phones import GEORGIA_MOBILE, GERMANY_MOBILE, ISRAEL_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed


@dataclass(frozen=True)
class Customers:
    testbed: AccountsTestbed
    owner_id: UserId
    staff_id: UserId
    business: BusinessDocument
    giorgi: SeededVisitor
    nino: SeededVisitor
    foreign: SeededVisitor


def seed_customers() -> Customers:
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
    giorgi = seed_visitor(testbed, business, "Giorgi", "+995577123456", "4242", "ka")
    testbed.clock.advance(60)
    nino = seed_visitor(testbed, business, "Nino", "+995577654321", "5353", "ru")
    foreign = seed_visitor(
        testbed, other_business, "Noa", "+972502223344", "6464", "he"
    )
    return Customers(
        testbed=testbed,
        owner_id=owner.user.id,
        staff_id=staff.user.id,
        business=business,
        giorgi=giorgi,
        nino=nino,
        foreign=foreign,
    )


def list_contacts(
    customers: Customers,
    search: str | None = None,
    page: PageRequest | None = None,
    user_id: UserId | None = None,
) -> ContactPage:
    return customers.testbed.list_contacts.run(
        ContactListQuery(
            user_id=customers.owner_id if user_id is None else user_id,
            business_id=customers.business.id,
            search=None if search is None else ContactSearchText(search),
            page=page or PageRequest(),
            client_ip_address=ClientIpAddress("192.0.2.10"),
        )
    )
