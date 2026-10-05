"""
The cabinet's search (Cmd/Ctrl+K): customers by name, phone digits or id,
their latest conversations and bookings, and a conversation or booking
named by its id; at most five of each, phones masked for staff, audited
when it found someone.
"""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.search import BusinessSearchQuery, BusinessSearchResults
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.search.constrained_strings import CabinetSearchText
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.search.search_business_use_case import SearchBusinessUseCase
from tests.customers.customer_bed import CLIENT_IP, CustomerBed, names_of
from tests.users.accounts_phones import USA_MOBILE


class SearchBed(CustomerBed):
    def __init__(self) -> None:
        super().__init__()
        testbed = self.customers.testbed
        self.search_business = SearchBusinessUseCase(
            authorize_business_access=testbed.authorize_business_access,
            contact_repo=testbed.contact_repo,
            conversation_repo=testbed.conversation_repo,
            booking_repo=testbed.booking_repo,
            contact_activity_repo=testbed.contact_activity_repo,
            customer_history_repo=testbed.customer_history_repo,
            customer_settings_repo=testbed.customer_settings_repo,
            audit_log_repo=testbed.audit_log_repo,
            wall_clock=testbed.clock.build_wall_clock(),
            phone_number_parser=testbed.phone_parser,
        )

    def search(self, text: str, user_id: UserId | None = None) -> BusinessSearchResults:
        return self.search_business.run(
            BusinessSearchQuery(
                user_id=user_id or self.owner_id,
                business_id=self.customers.business.id,
                text=CabinetSearchText(text),
                client_ip_address=CLIENT_IP,
            )
        )

    def searches_audited(self) -> int:
        return sum(
            1
            for entry in self.customers.testbed.audit_log_repo.list_by_business(
                self.customers.business.id
            )
            if entry.entity == "customer_search"
        )


def test_a_name_finds_the_customer_with_their_conversations_and_bookings() -> None:
    bed = SearchBed()
    nino = bed.customers.nino

    found = bed.search("nino")

    assert names_of(found.customers) == ["Nino"]
    assert found.customers[0].phone_number == "+995577654321"
    assert {hit.id for hit in found.conversations} == {
        nino.chat_conversation.id,
        nino.phone_conversation.id,
    }
    assert all(str(hit.contact_name) == "Nino" for hit in found.conversations)
    assert [(hit.id, str(hit.contact_name)) for hit in found.bookings] == [
        (nino.booking.id, "Nino")
    ]
    entry = bed.customers.testbed.audit_log_repo.list_by_business(
        bed.customers.business.id
    )[-1]
    assert (entry.action, entry.entity, entry.actor_id, entry.ip_address) == (
        AuditAction.VIEW,
        "customer_search",
        bed.owner_id,
        "192.0.2.10",
    )


def test_phone_digits_find_customers_and_staff_see_them_masked() -> None:
    bed = SearchBed()

    found = bed.search("+995 577", user_id=bed.staff_id)

    assert names_of(found.customers) == ["Nino", "Giorgi"]
    assert [row.phone_number for row in found.customers] == [None, None]
    assert [str(row.masked_phone_number) for row in found.customers] == [
        "+995 ••• ••• •21",
        "+995 ••• ••• •56",
    ]
    assert len(found.conversations) == 4


def test_an_id_names_one_conversation_or_booking() -> None:
    bed = SearchBed()
    giorgi = bed.customers.giorgi

    by_conversation = bed.search(str(giorgi.phone_conversation.id))
    by_booking = bed.search(str(giorgi.booking.id))
    by_contact = bed.search(str(giorgi.contact.id))

    assert [hit.id for hit in by_conversation.conversations] == [
        giorgi.phone_conversation.id
    ]
    assert by_conversation.customers == []
    assert [hit.id for hit in by_booking.bookings] == [giorgi.booking.id]
    assert names_of(by_contact.customers) == ["Giorgi"]


def test_each_group_holds_at_most_five_hits() -> None:
    bed = SearchBed()
    for index in range(7):
        bed.customers.testbed.contact_repo.save(
            ContactDocument(
                business_id=bed.customers.business.id,
                name=ContactName(f"Tamar {index}"),
            )
        )

    found = bed.search("tamar")

    assert len(found.customers) == 5


def test_nothing_found_is_not_audited() -> None:
    bed = SearchBed()

    found = bed.search("nobody here")
    foreign = bed.search(str(bed.customers.foreign.chat_conversation.id))
    blank = bed.search("   ")

    for results in (found, foreign, blank):
        assert results == BusinessSearchResults()
    assert bed.searches_audited() == 0


def test_test_chats_are_not_found_by_id() -> None:
    bed = SearchBed()
    giorgi = bed.customers.giorgi
    sandbox = giorgi.chat_conversation.model_copy(update={"is_sandbox": True})
    bed.customers.testbed.conversation_repo.save(sandbox)

    found = bed.search(str(sandbox.id))

    assert found.conversations == []


def test_strangers_cannot_search_a_business() -> None:
    bed = SearchBed()
    stranger = bed.customers.testbed.sign_in_with_phone(USA_MOBILE)

    with pytest.raises(NotFoundError):
        bed.search("nino", user_id=stranger.user.id)
