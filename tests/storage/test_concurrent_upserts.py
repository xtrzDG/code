"""Many threads writing through one small pool: no lost rows, no errors."""

import threading

from psycopg import sql

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.builders import COUNTRY_SAMPLES, build_knowledge_item
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.storage_testing import build_ticking_wall_clock

THREAD_COUNT: int = 12
WRITES_PER_THREAD: int = 20
POOL_SIZE: int = 4
SHARED_KEY: str = "shared-price"


def count_rows(connection_pool: PostgresConnectionPoolClient) -> tuple[int, int]:
    with connection_pool.transaction() as connection:
        connection.execute("select set_config('app.bypass_rls', 'on', true)")
        row = connection.execute(
            sql.SQL("select count(*), count(distinct document_key) from {}").format(
                sql.Identifier("workshop", "knowledge_items")
            )
        ).fetchone()

    assert row is not None
    total: object = row[0]
    distinct: object = row[1]
    assert isinstance(total, int)
    assert isinstance(distinct, int)
    return total, distinct


def test_concurrent_upserts_through_a_small_pool(database_url: DatabaseUrl) -> None:
    connection_pool = PostgresConnectionPoolClient(
        database_url,
        max_size=POOL_SIZE,
        acquire_timeout_seconds=30,
    )
    storage_scope = StorageScopeContext()
    knowledge_items = PostgresCollectionFactory(
        connection_pool=connection_pool,
        storage_scope=storage_scope,
        wall_clock=build_ticking_wall_clock(),
    )(KnowledgeItemDocument, "knowledge_items")
    business_ids = [BusinessId() for _ in range(THREAD_COUNT)]
    written_prices: set[int] = set()
    errors: list[BaseException] = []
    start = threading.Barrier(THREAD_COUNT)
    lock = threading.Lock()

    def write(thread_index: int) -> None:
        sample = COUNTRY_SAMPLES[thread_index % len(COUNTRY_SAMPLES)]
        business_id = business_ids[thread_index]
        try:
            start.wait()
            for write_index in range(WRITES_PER_THREAD):
                # Own rows, written inside the thread's business scope.
                with storage_scope.scoped_to_business(business_id):
                    item = build_knowledge_item(sample, business_id)
                    knowledge_items.upsert(str(item.id), item)

                # One row that every thread overwrites (platform-wide).
                price = thread_index * 1000 + write_index
                with lock:
                    written_prices.add(price)
                shared_item = build_knowledge_item(sample, business_id)
                shared_item.price_minor = MoneyAmountMinor(price)
                knowledge_items.upsert(SHARED_KEY, shared_item)
        except BaseException as error:  # pragma: no cover - reported below
            errors.append(error)

    threads = [
        threading.Thread(target=write, args=(thread_index,))
        for thread_index in range(THREAD_COUNT)
    ]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        total_rows, distinct_keys = count_rows(connection_pool)
        shared_item = knowledge_items.get(SHARED_KEY)
        visible_counts: dict[BusinessId, int] = {}
        for business_id in business_ids:
            with storage_scope.scoped_to_business(business_id):
                visible_items = knowledge_items.list_all()
            assert {item.business_id for item in visible_items} <= {business_id}
            visible_counts[business_id] = len(visible_items)
        open_connections = connection_pool.open_connection_count()
    finally:
        connection_pool.close()

    assert errors == []
    expected_rows = THREAD_COUNT * WRITES_PER_THREAD + 1
    assert (total_rows, distinct_keys) == (expected_rows, expected_rows)
    assert shared_item is not None
    assert shared_item.price_minor in written_prices
    assert shared_item.business_id in business_ids
    # Each business sees its own rows, plus the shared row if it wrote last.
    assert visible_counts == {
        business_id: WRITES_PER_THREAD
        + (1 if business_id == shared_item.business_id else 0)
        for business_id in business_ids
    }
    assert open_connections <= POOL_SIZE
