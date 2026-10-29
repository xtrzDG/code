"""
The customer list as keyset pages (migration 1122): the most recently
active first, exact search matches from indexes and partial ones from a
bounded walk that "Load more" continues.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.dto.contacts import ContactPage
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.use_cases.shared.contact_activity import (
    LAST_SEEN_STEP_MICROSECONDS,
    mark_contact_seen,
)
from app.use_cases.shared.contact_search_scan import SEARCH_SCAN_LIMIT
from tests.compliance.customer_records import Customers, list_contacts, seed_customers

START: int = 1_700_000_000_000_000


def add_customers(customers: Customers, names: list[str]) -> list[ContactDocument]:
    """Contacts first seen one second apart, in the order given."""

    contacts: list[ContactDocument] = [
        ContactDocument(
            business_id=customers.business.id,
            name=ContactName(name),
            created_at=Microseconds(START + index * 1_000_000),
            updated_at=Microseconds(START + index * 1_000_000),
        )
        for index, name in enumerate(names)
    ]
    customers.testbed.contact_repo.save_many(contacts)
    return contacts


def names(page: ContactPage) -> list[str]:
    return [str(item.name) for item in page.items]


def walk(customers: Customers, search: str | None, size: int) -> list[list[str]]:
    """Every page of a list or a search, following its cursors."""

    pages: list[list[str]] = []
    cursor: PageCursor | None = None
    while True:
        page = list_contacts(
            customers, search, PageRequest(size=PageSize(size), cursor=cursor)
        )
        pages.append(names(page))
        cursor = page.next_cursor
        if cursor is None:
            return pages


def test_the_list_pages_the_most_recently_active_customers_first() -> None:
    customers = seed_customers()
    add_customers(customers, [f"Guest {index}" for index in range(5)])

    pages = walk(customers, None, 3)

    assert [name for page in pages for name in page] == [
        "Nino",
        "Giorgi",
        "Guest 4",
        "Guest 3",
        "Guest 2",
        "Guest 1",
        "Guest 0",
    ]
    assert [len(page) for page in pages] == [3, 3, 1]


def test_an_exact_name_is_found_however_long_ago_the_customer_was_seen() -> None:
    customers = seed_customers()
    add_customers(
        customers,
        ["Tamar Beridze"] + [f"Guest {index}" for index in range(SEARCH_SCAN_LIMIT)],
    )

    exact = list_contacts(customers, "TAMAR beridze")
    partial = walk(customers, "Tamar", 10)

    assert names(exact) == ["Tamar Beridze"]
    # Part of a name has no index: the first request looks at the latest
    # customers only and leaves a cursor; "Load more" reaches Tamar.
    assert partial[0] == []
    assert [name for page in partial for name in page] == ["Tamar Beridze"]


def test_exact_matches_lead_the_first_page_and_never_come_again() -> None:
    customers = seed_customers()
    add_customers(customers, ["Ana", "Anano", "Ana", "Anastasia", "Ana Maria"])

    pages = walk(customers, "ana", 2)
    found = [name for page in pages for name in page]

    # The newer exact "Ana" leads, the older one comes as the walk reaches it.
    assert found[0] == "Ana"
    assert sorted(found) == sorted(["Ana", "Anano", "Ana", "Anastasia", "Ana Maria"])
    assert all(len(page) <= 2 for page in pages)


def test_a_contact_made_only_by_tests_is_never_marked_seen() -> None:
    tester = ContactDocument(
        business_id=seed_customers().business.id,
        channel_identities=[
            ChannelIdentity(
                channel=ChannelKind.OWNER_TEST,
                channel_user_id=ChannelUserId("owner:1:default"),
            )
        ],
        created_at=Microseconds(START),
        updated_at=Microseconds(START),
    )

    assert tester.last_seen_at is None
    assert mark_contact_seen(tester, Microseconds(START + 10**9)) is False
    assert tester.last_seen_at is None


def test_a_busy_conversation_moves_the_contact_once_per_step() -> None:
    contact = ContactDocument(
        business_id=seed_customers().business.id,
        created_at=Microseconds(START),
        updated_at=Microseconds(START),
    )
    soon = Microseconds(START + LAST_SEEN_STEP_MICROSECONDS - 1)
    later = Microseconds(START + LAST_SEEN_STEP_MICROSECONDS)

    assert contact.last_seen_at == START
    assert mark_contact_seen(contact, soon) is False
    assert contact.last_seen_at == START
    assert mark_contact_seen(contact, later) is True
    assert contact.last_seen_at == later


def test_a_returning_customer_moves_to_the_top_of_the_list() -> None:
    customers = seed_customers()
    giorgi = customers.testbed.contact_repo.get(
        customers.business.id, customers.giorgi.contact.id
    )
    assert giorgi is not None
    assert giorgi.last_seen_at is not None
    mark_contact_seen(
        giorgi, Microseconds(int(giorgi.last_seen_at) + LAST_SEEN_STEP_MICROSECONDS * 3)
    )
    customers.testbed.contact_repo.save(giorgi)

    assert names(list_contacts(customers)) == ["Giorgi", "Nino"]
