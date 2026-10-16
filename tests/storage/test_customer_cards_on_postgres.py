"""
The customer card on Postgres (1140): two colleagues changing one card at
once are serialised by the row lock (no retry, nothing lost), and rows
written before the VIP and blocked columns existed get their values from
the 1122 backfill (`workshop backfill-lookup`).
"""

import threading
from collections.abc import Callable

import pytest
from typed_time_provider import Microseconds

from app.adapters.storage.postgres.postgres_lookup_backfill_adapter import (
    PostgresLookupBackfillAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.repositories.conversation_repositories import ContactRepository
from app.schemas.domain.contacts import ContactBlock, ContactDocument
from app.schemas.dto.customers.customer_records import CustomerPageFilter
from app.schemas.dto.lookup_backfill import BackfillLookupColumnsCommand
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.booleans import (
    IsBlockedOnlyFilter,
    IsVipOnlyFilter,
)
from app.schemas.typings.contacts.constrained_strings import CustomerTag
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.maintenance.backfill_lookup_columns_use_case import (
    BackfillLookupColumnsUseCase,
)
from app.utilities.customers.customer_card import add_tags
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.storage_testing import RecordedRetryPause

pytestmark = pytest.mark.usefixtures("platform_scope")

BUSINESS: BusinessId = BusinessId()
PAGE = KeysetSlice(limit=KeysetReadLimit(10))
WAIT_SECONDS: float = 10.0


def seeded(
    collections: PostgresCollectionFactory,
) -> tuple[ContactRepository, ContactDocument]:
    repo = ContactRepository(collections(ContactDocument, "contacts"))
    contact = ContactDocument(
        business_id=BUSINESS, name=ContactName("Giorgi"), last_seen_at=Microseconds(1)
    )
    repo.save(contact)
    return repo, contact


def test_two_card_changes_at_once_wait_for_each_other(
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    repo, contact = seeded(postgres_collections)
    owner, staff = UserId(), UserId()
    first_inside, release_first = threading.Event(), threading.Event()
    second_applied = threading.Event()
    seen_by_second: list[list[str]] = []
    errors: list[Exception] = []

    def first_change(stored: ContactDocument) -> None:
        add_tags(stored, [CustomerTag("regular")], owner, Microseconds(5))
        first_inside.set()
        assert release_first.wait(WAIT_SECONDS)

    def second_change(stored: ContactDocument) -> None:
        seen_by_second.append([str(mark.tag) for mark in stored.tags])
        add_tags(stored, [CustomerTag("terrace")], staff, Microseconds(6))
        second_applied.set()

    def run(change: Callable[[ContactDocument], None]) -> None:
        try:
            with storage_scope.scoped_to_business(BUSINESS):
                repo.change_card(BUSINESS, contact.id, change)
        except Exception as error:  # reported below
            errors.append(error)
            first_inside.set()

    first = threading.Thread(target=run, args=(first_change,))
    first.start()
    assert first_inside.wait(WAIT_SECONDS)
    second = threading.Thread(target=run, args=(second_change,))
    second.start()
    # The first change holds the row: the second cannot read it yet.
    assert not second_applied.wait(0.5)
    release_first.set()
    first.join(WAIT_SECONDS)
    second.join(WAIT_SECONDS)

    assert errors == []
    assert seen_by_second == [["regular"]]
    stored = repo.get(BUSINESS, contact.id)
    assert stored is not None
    assert [str(mark.tag) for mark in stored.tags] == ["regular", "terrace"]


def test_the_backfill_fills_the_card_columns_of_older_rows(
    postgres_collections: PostgresCollectionFactory,
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    repo, contact = seeded(postgres_collections)

    def mark(stored: ContactDocument) -> None:
        stored.is_vip = True
        stored.block = ContactBlock(blocked_at=Microseconds(5), blocked_by=UserId())

    repo.change_card(BUSINESS, contact.id, mark)
    # As if written before 1140: the columns are empty.
    with connection_pool.transaction() as connection:
        connection.execute("select set_config('app.bypass_rls', 'on', true)")
        connection.execute(
            "update workshop.contacts set doc_is_vip = null, doc_is_blocked = null"
        )
    vip = CustomerPageFilter(vip_only=IsVipOnlyFilter(True))
    blocked = CustomerPageFilter(blocked_only=IsBlockedOnlyFilter(True))
    assert repo.page_customers(BUSINESS, PAGE, vip) == []

    report = BackfillLookupColumnsUseCase(
        backfill=PostgresLookupBackfillAdapter(
            connection_pool, lock_timeout=LockWaitSeconds(1)
        ),
        retry_pause=RecordedRetryPause(),
    ).run(
        BackfillLookupColumnsCommand(collection_name=DocumentCollectionName("contacts"))
    )

    filled = {str(entry.field): int(entry.filled) for entry in report.columns}
    assert sum(filled.values()) == 1
    assert [row.id for row in repo.page_customers(BUSINESS, PAGE, vip)] == [contact.id]
    assert [row.id for row in repo.page_customers(BUSINESS, PAGE, blocked)] == [
        contact.id
    ]
