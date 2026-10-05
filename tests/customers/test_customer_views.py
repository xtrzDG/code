"""
A customer's page and the list as the team sees them: phones masked for
staff unless the owner allows them, every view audited, the timeline
across channels newest first, the standing, and the list's filters.
"""

import pytest

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.customers import (
    CustomerListFilter,
    CustomerStanding,
    CustomerTimelineKind,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.contacts import ContactListQuery, ContactPage
from app.schemas.dto.customers.customer_card import ContactStandingQuery
from app.schemas.dto.customers.customer_settings import (
    CustomerSettingsRequest,
    UpdateCustomerSettingsCommand,
)
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.contacts.booleans import StaffSeesCustomerPhones
from app.schemas.typings.contacts.constrained_strings import (
    ContactSearchText,
    CustomerTag,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.customer_phone_privacy import mask_phone_number
from tests.customers.customer_bed import CLIENT_IP, CustomerBed, names_of


def list_customers(
    bed: CustomerBed,
    user_id: UserId | None = None,
    tag: str | None = None,
    list_filter: CustomerListFilter = CustomerListFilter.ALL,
    search: str | None = None,
) -> ContactPage:
    return bed.customers.testbed.list_contacts.run(
        ContactListQuery(
            user_id=user_id or bed.owner_id,
            business_id=bed.customers.business.id,
            tag=None if tag is None else CustomerTag(tag),
            list_filter=list_filter,
            search=None if search is None else ContactSearchText(search),
            client_ip_address=CLIENT_IP,
        )
    )


@pytest.mark.parametrize(
    ("phone_number", "masked"),
    [
        ("+995577123456", "+995 ••• ••• •56"),
        ("+14155550123", "+141 •• ••• •23"),
        ("+3725123", "+372 • •23"),
    ],
)
def test_a_masked_phone_keeps_the_country_and_the_last_digits(
    phone_number: str, masked: str
) -> None:
    assert mask_phone_number(E164PhoneNumber(phone_number)) == masked


def test_staff_see_a_customer_with_the_phone_masked_and_the_view_is_audited() -> None:
    bed = CustomerBed()
    giorgi = bed.customers.giorgi.contact

    detail = bed.customers.testbed.get_contact.run(
        bed.contact_query(giorgi.id, user_id=bed.staff_id)
    )

    assert detail.contact.phone_number is None
    assert detail.contact.masked_phone_number == "+995 ••• ••• •56"
    assert detail.contact.is_phone_masked is True
    entry = bed.customers.testbed.audit_log_repo.list_by_business(
        bed.customers.business.id
    )[-1]
    assert (entry.action, entry.entity, entry.entity_id, entry.actor_id) == (
        AuditAction.VIEW,
        "contact",
        str(giorgi.id),
        bed.staff_id,
    )


def test_staff_see_phones_once_the_owner_allows_it() -> None:
    bed = CustomerBed()
    bed.allow_staff_phones()

    page = list_customers(bed, user_id=bed.staff_id)
    detail = bed.customers.testbed.get_contact.run(
        bed.contact_query(bed.customers.nino.contact.id, user_id=bed.staff_id)
    )

    assert [row.phone_number for row in page.items] == [
        "+995577654321",
        "+995577123456",
    ]
    assert all(row.is_phone_masked is False for row in page.items)
    assert detail.contact.phone_number == "+995577654321"
    bed.allow_staff_phones(is_allowed=False)
    assert list_customers(bed, user_id=bed.staff_id).items[0].phone_number is None


def test_only_owners_change_who_sees_phones_and_the_change_is_audited() -> None:
    bed = CustomerBed()
    with pytest.raises(AccessDeniedError):
        bed.update_settings.run(
            UpdateCustomerSettingsCommand(
                user_id=bed.staff_id,
                business_id=bed.customers.business.id,
                request=CustomerSettingsRequest(
                    staff_sees_phone_numbers=StaffSeesCustomerPhones(True)
                ),
            )
        )

    bed.allow_staff_phones()

    entry = bed.customers.testbed.audit_log_repo.list_by_business(
        bed.customers.business.id
    )[-1]
    assert (entry.action, entry.entity) == (AuditAction.UPDATE, "customer_settings")


def test_the_timeline_lists_every_channel_newest_first() -> None:
    bed = CustomerBed()
    giorgi = bed.customers.giorgi
    long_ago = bed.add_booking(giorgi.contact.id, days_ago=40)
    recent = bed.add_booking(giorgi.contact.id, days_ago=3)

    detail = bed.customers.testbed.get_contact.run(bed.contact_query(giorgi.contact.id))

    timeline = detail.timeline
    moments = [int(entry.occurred_at) for entry in timeline]
    assert moments == sorted(moments, reverse=True)
    assert {(entry.kind, entry.conversation_id) for entry in timeline} == {
        (CustomerTimelineKind.CONVERSATION, giorgi.chat_conversation.id),
        (CustomerTimelineKind.CONVERSATION, giorgi.phone_conversation.id),
        (CustomerTimelineKind.LEAD, giorgi.chat_conversation.id),
        (CustomerTimelineKind.CALL, giorgi.phone_conversation.id),
        (CustomerTimelineKind.BOOKING, giorgi.chat_conversation.id),
        (CustomerTimelineKind.BOOKING, None),
    }
    # The upcoming booking comes before the conversations of today; the
    # visits of the past close the list.
    kinds = [entry.kind for entry in timeline]
    upcoming = [entry.booking_id for entry in timeline].index(giorgi.booking.id)
    assert upcoming < kinds.index(CustomerTimelineKind.CONVERSATION)
    assert [entry.booking_id for entry in timeline[-2:]] == [recent.id, long_ago.id]
    call = next(entry for entry in timeline if entry.kind is CustomerTimelineKind.CALL)
    assert call.call_id == giorgi.conversation_call.id


def test_two_visits_make_a_regular_customer() -> None:
    bed = CustomerBed()
    giorgi = bed.customers.giorgi.contact
    bed.add_booking(giorgi.id, days_ago=40)
    recent = bed.add_booking(giorgi.id, days_ago=3, status=BookingStatus.CONFIRMED)
    bed.add_booking(giorgi.id, days_ago=10, status=BookingStatus.CANCELLED)
    bed.add_booking(giorgi.id, days_ago=12, status=BookingStatus.NO_SHOW)
    audited = len(
        bed.customers.testbed.audit_log_repo.list_by_business(giorgi.business_id)
    )

    standing = bed.get_standing.run(
        ContactStandingQuery(
            user_id=bed.staff_id,
            business_id=giorgi.business_id,
            contact_id=giorgi.id,
        )
    )
    detail = bed.customers.testbed.get_contact.run(bed.contact_query(giorgi.id))

    assert standing.standing is CustomerStanding.REGULAR
    assert standing.visit_count == 2
    assert standing.last_visit_at == int(recent.starts_at) * 1_000_000
    assert (standing.conversation_count, standing.booking_count) == (2, 5)
    assert (detail.standing, detail.visit_count) == (CustomerStanding.REGULAR, 2)
    # The standing names no personal data: it is not audited.
    assert (
        len(bed.customers.testbed.audit_log_repo.list_by_business(giorgi.business_id))
        == audited + 1
    )


def test_standing_without_visits_tells_new_from_returning_customers() -> None:
    bed = CustomerBed()
    walk_in = ContactDocument(business_id=bed.customers.business.id)
    bed.customers.testbed.contact_repo.save(walk_in)
    nino = bed.customers.nino.contact
    bed.add_booking(nino.id, days_ago=5)

    def standing_of(contact_id: ContactId) -> CustomerStanding:
        return bed.get_standing.run(
            ContactStandingQuery(
                user_id=bed.owner_id,
                business_id=bed.customers.business.id,
                contact_id=contact_id,
            )
        ).standing

    assert standing_of(walk_in.id) is CustomerStanding.NEW
    assert standing_of(bed.customers.giorgi.contact.id) is CustomerStanding.RETURNING
    assert standing_of(nino.id) is CustomerStanding.VISITED


def test_the_list_filters_by_tag_vip_and_block() -> None:
    bed = CustomerBed()
    giorgi = bed.customers.giorgi.contact
    nino = bed.customers.nino.contact
    bed.tag(giorgi.id, "Regular", is_vip=True)
    bed.tag(nino.id, "regular")
    bed.block(nino.id)

    assert names_of(list_customers(bed, tag="REGULAR").items) == ["Nino", "Giorgi"]
    assert names_of(list_customers(bed, list_filter=CustomerListFilter.VIP).items) == [
        "Giorgi"
    ]
    blocked = list_customers(bed, list_filter=CustomerListFilter.BLOCKED).items
    assert names_of(blocked) == ["Nino"]
    assert blocked[0].is_blocked is True
    assert [str(tag) for tag in blocked[0].tags] == ["regular"]
    assert names_of(list_customers(bed, tag="regular", search="gior").items) == [
        "Giorgi"
    ]
    assert list_customers(bed, tag="terrace").items == []
    assert names_of(
        list_customers(
            bed, user_id=bed.staff_id, list_filter=CustomerListFilter.VIP
        ).items
    ) == ["Giorgi"]
