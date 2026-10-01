"""The customer list for data requests and one customer's page."""

from dataclasses import dataclass

import pytest

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.dto.businesses import InviteStaffCommand, InviteStaffRequest
from app.schemas.dto.compliance import ContactDataCommand
from app.schemas.dto.contacts import ContactListQuery, ContactPage, ContactQuery
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.constrained_strings import ContactSearchText
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.users.prefixed_id import UserId
from tests.compliance.visitor_records import (
    SeededVisitor,
    build_conversation,
    seed_visitor,
)
from tests.users.accounts_testbed import (
    GEORGIA_MOBILE,
    GERMANY_MOBILE,
    ISRAEL_MOBILE,
    AccountsTestbed,
    build_accounts_testbed,
)


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


def test_owner_lists_the_customers_of_the_business_most_recent_first() -> None:
    customers = seed_customers()

    page = list_contacts(customers)

    assert [str(item.name) for item in page.items] == ["Nino", "Giorgi"]
    assert page.next_cursor is None
    giorgi = page.items[1]
    assert giorgi.id == customers.giorgi.contact.id
    assert giorgi.phone_number == "+995577123456"
    assert giorgi.is_phone_verified is False
    assert giorgi.language == "ka"
    assert giorgi.channels == [ChannelKind.PHONE, ChannelKind.TELEGRAM]
    assert (giorgi.conversation_count, giorgi.booking_count, giorgi.lead_count) == (
        2,
        1,
        1,
    )
    assert giorgi.erased_at is None
    entries = customers.testbed.audit_log_repo.list_by_business(customers.business.id)
    assert (entries[-1].action, entries[-1].entity, entries[-1].entity_id) == (
        AuditAction.VIEW,
        "contact",
        None,
    )
    assert entries[-1].ip_address == "192.0.2.10"


@pytest.mark.parametrize(
    ("search", "names"),
    [
        ("nino", ["Nino"]),
        ("GIOR", ["Giorgi"]),
        ("577 65", ["Nino"]),
        ("+995 577", ["Nino", "Giorgi"]),
        ("٦٥٤٣٢١", ["Nino"]),
        ("57", []),
        ("Noa", []),
    ],
)
def test_search_matches_names_and_phone_digits(search: str, names: list[str]) -> None:
    customers = seed_customers()

    page = list_contacts(customers, search)

    assert [str(item.name) for item in page.items] == names


def test_search_by_contact_id_finds_exactly_that_customer() -> None:
    customers = seed_customers()

    page = list_contacts(customers, str(customers.giorgi.contact.id))

    assert [item.id for item in page.items] == [customers.giorgi.contact.id]


def test_customers_are_paged_with_a_cursor() -> None:
    customers = seed_customers()

    first = list_contacts(customers, page=PageRequest(size=PageSize(1)))
    second = list_contacts(
        customers,
        page=PageRequest(size=PageSize(1), cursor=first.next_cursor),
    )

    assert [str(item.name) for item in first.items] == ["Nino"]
    assert first.next_cursor is not None
    assert [str(item.name) for item in second.items] == ["Giorgi"]
    assert second.next_cursor is None


def test_test_chat_customers_are_left_out() -> None:
    customers = seed_customers()
    tester = ContactDocument(
        business_id=customers.business.id,
        channel_identities=[
            ChannelIdentity(
                channel=ChannelKind.OWNER_TEST,
                channel_user_id=ChannelUserId("owner:1:default"),
            )
        ],
    )
    customers.testbed.contact_repo.save(tester)
    sandbox = build_conversation(
        customers.business,
        tester,
        ChannelKind.OWNER_TEST,
        "owner:1:default",
        customers.testbed.clock.now_microseconds(),
    )
    sandbox.is_sandbox = True
    customers.testbed.conversation_repo.save(sandbox)
    walk_in = ContactDocument(business_id=customers.business.id)
    customers.testbed.contact_repo.save(walk_in)

    ids = [item.id for item in list_contacts(customers).items]

    assert tester.id not in ids
    assert walk_in.id in ids


def test_only_owners_list_customers() -> None:
    customers = seed_customers()

    with pytest.raises(AccessDeniedError):
        list_contacts(customers, user_id=customers.staff_id)


def test_owner_opens_one_customer_and_the_view_is_audited() -> None:
    customers = seed_customers()
    giorgi = customers.giorgi

    detail = customers.testbed.get_contact.run(
        ContactQuery(
            user_id=customers.owner_id,
            business_id=customers.business.id,
            contact_id=giorgi.contact.id,
            client_ip_address=ClientIpAddress("192.0.2.10"),
        )
    )

    assert detail.contact.name == "Giorgi"
    assert {item.id for item in detail.conversations} == {
        giorgi.chat_conversation.id,
        giorgi.phone_conversation.id,
    }
    assert [item.id for item in detail.bookings] == [giorgi.booking.id]
    assert [item.id for item in detail.leads] == [giorgi.lead.id]
    entry = customers.testbed.audit_log_repo.list_by_business(customers.business.id)[-1]
    assert (entry.action, entry.entity, entry.entity_id) == (
        AuditAction.VIEW,
        "contact",
        str(giorgi.contact.id),
    )


def test_customers_of_another_business_are_not_found() -> None:
    customers = seed_customers()

    for contact_id in (customers.foreign.contact.id, ContactId()):
        with pytest.raises(NotFoundError):
            customers.testbed.get_contact.run(
                ContactQuery(
                    user_id=customers.owner_id,
                    business_id=customers.business.id,
                    contact_id=contact_id,
                )
            )


def test_an_erased_customer_stays_in_the_list_marked_erased() -> None:
    customers = seed_customers()
    giorgi = customers.giorgi
    customers.testbed.clock.advance(3600)
    customers.testbed.delete_contact_data.run(
        ContactDataCommand(
            user_id=customers.owner_id,
            business_id=customers.business.id,
            contact_id=giorgi.contact.id,
        )
    )

    page = list_contacts(customers)
    detail = customers.testbed.get_contact.run(
        ContactQuery(
            user_id=customers.owner_id,
            business_id=customers.business.id,
            contact_id=giorgi.contact.id,
        )
    )

    erased = next(item for item in page.items if item.id == giorgi.contact.id)
    erased_at = customers.testbed.clock.now_microseconds()
    assert erased.erased_at == erased_at
    assert erased.last_activity_at >= erased_at
    assert (erased.name, erased.phone_number, erased.language) == (None, None, None)
    assert erased.conversation_count == 2
    assert detail.contact.erased_at == erased.erased_at
    assert list_contacts(customers, "Giorgi").items == []
