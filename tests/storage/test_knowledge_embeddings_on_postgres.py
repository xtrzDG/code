"""
The knowledge vectors in pgvector (migration 1211): without the extension
the store is unavailable and the search stays lexical; once an
administrator created it and `workshop.enable_knowledge_embeddings()` ran,
vectors are stored per business under row-level security and ranked by
cosine distance.
"""

from collections.abc import Generator

import pytest

from app.adapters.embeddings.postgres_knowledge_embedding_store_adapter import (
    PostgresKnowledgeEmbeddingStoreAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_integers import EmbeddingNeighbourLimit
from app.schemas.typings.knowledge.constrained_strings import (
    EmbeddingModelId,
    KnowledgeEmbeddingFingerprint,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import build_fixed_wall_clock

MODEL = EmbeddingModelId("text-embedding-3-small")
OTHER_MODEL = EmbeddingModelId("text-embedding-3-large")
TBILISI = BusinessId("business_6f1c7a2e-3b4d-4e5f-8a9b-0c1d2e3f4a5b")
HAIFA = BusinessId("business_1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d")


def fingerprint(character: str) -> KnowledgeEmbeddingFingerprint:
    return KnowledgeEmbeddingFingerprint(character * 64)


def build_store(
    connection_pool: PostgresConnectionPoolClient, storage_scope: StorageScopeContext
) -> PostgresKnowledgeEmbeddingStoreAdapter:
    return PostgresKnowledgeEmbeddingStoreAdapter(
        connection_pool, storage_scope, build_fixed_wall_clock()
    )


@pytest.fixture
def vector_database(
    postgres_server: ThrowawayPostgresServer, database_name: str
) -> Generator[str]:
    """The migrated database after an administrator enabled pgvector."""

    with postgres_server.admin_connection(database_name) as admin:
        available = admin.execute(
            "select 1 from pg_available_extensions where name = 'vector'"
        ).fetchone()
        if available is None:
            pytest.skip("pgvector is not installed on this Postgres server.")

        admin.execute("create extension if not exists vector")

    with postgres_server.app_connection(database_name) as app:
        enabled = app.execute(
            "select workshop.enable_knowledge_embeddings()"
        ).fetchone()
        app.commit()
    assert enabled == (True,)
    yield database_name


def test_without_pgvector_the_migration_changes_nothing_and_the_store_is_off(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
    connection_pool: PostgresConnectionPoolClient,
    storage_scope: StorageScopeContext,
) -> None:
    # The application's role may not create the (untrusted) extension, as on
    # a managed server before an administrator enabled it.
    with postgres_server.app_connection(database_name) as app:
        table = app.execute(
            "select to_regclass('workshop.knowledge_embeddings')"
        ).fetchone()
        enabled = app.execute(
            "select workshop.enable_knowledge_embeddings()"
        ).fetchone()
    store = build_store(connection_pool, storage_scope)

    assert table == (None,)
    assert enabled == (False,)
    assert not store.is_available()
    with storage_scope.scoped_to_business(TBILISI):
        assert store.read_fingerprints(TBILISI) == {}
        assert (
            store.nearest(TBILISI, MODEL, (1.0, 0.0), EmbeddingNeighbourLimit(5)) == []
        )
        store.save(TBILISI, MODEL, [(KnowledgeItemId(), fingerprint("a"), (1.0, 0.0))])
        store.delete(TBILISI, [KnowledgeItemId()])


def test_vectors_are_ranked_by_meaning_per_business_and_model(
    postgres_server: ThrowawayPostgresServer,
    vector_database: str,
    storage_scope: StorageScopeContext,
) -> None:
    pool = PostgresConnectionPoolClient(
        postgres_server.app_database_url(vector_database), max_size=4
    )
    try:
        store = build_store(pool, storage_scope)
        parking, music, garage = KnowledgeItemId(), KnowledgeItemId(), KnowledgeItemId()
        haifa_parking = KnowledgeItemId()
        with storage_scope.scoped_to_business(TBILISI):
            store.save(
                TBILISI,
                MODEL,
                [
                    (parking, fingerprint("a"), (0.9, 0.1, 0.0)),
                    (music, fingerprint("b"), (0.0, 0.2, 0.98)),
                ],
            )
            store.save(TBILISI, OTHER_MODEL, [(garage, fingerprint("c"), (1.0, 0.0))])
        with storage_scope.scoped_to_business(HAIFA):
            store.save(
                HAIFA, MODEL, [(haifa_parking, fingerprint("d"), (1.0, 0.0, 0.0))]
            )

        with storage_scope.scoped_to_business(TBILISI):
            nearest = store.nearest(
                TBILISI, MODEL, (1.0, 0.0, 0.0), EmbeddingNeighbourLimit(5)
            )
            fingerprints = store.read_fingerprints(TBILISI)
            # A replaced vector takes the new fingerprint; a deleted one is gone.
            store.save(TBILISI, MODEL, [(parking, fingerprint("e"), (0.8, 0.2, 0.0))])
            store.delete(TBILISI, [music])
            after = store.read_fingerprints(TBILISI)

        assert [neighbour.item_id for neighbour in nearest] == [parking, music]
        assert float(nearest[0].similarity) == pytest.approx(
            0.9 / (0.82**0.5), abs=1e-4
        )
        assert fingerprints == {
            parking: fingerprint("a"),
            music: fingerprint("b"),
            garage: fingerprint("c"),
        }
        assert after == {parking: fingerprint("e"), garage: fingerprint("c")}
    finally:
        pool.close()


def test_row_level_security_keeps_a_business_to_its_own_vectors(
    postgres_server: ThrowawayPostgresServer,
    vector_database: str,
    storage_scope: StorageScopeContext,
) -> None:
    pool = PostgresConnectionPoolClient(
        postgres_server.app_database_url(vector_database), max_size=4
    )
    try:
        store = build_store(pool, storage_scope)
        with storage_scope.scoped_to_business(HAIFA):
            store.save(
                HAIFA, MODEL, [(KnowledgeItemId(), fingerprint("d"), (1.0, 0.0))]
            )

        with storage_scope.scoped_to_business(TBILISI):
            # Even when the query names the other business, RLS hides its rows.
            assert store.read_fingerprints(HAIFA) == {}
            assert (
                store.nearest(HAIFA, MODEL, (1.0, 0.0), EmbeddingNeighbourLimit(5))
                == []
            )
            with pytest.raises(AccessDeniedError):
                store.save(
                    HAIFA, MODEL, [(KnowledgeItemId(), fingerprint("f"), (1.0, 0.0))]
                )
    finally:
        pool.close()
