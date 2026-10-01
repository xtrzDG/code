"""CRUD round trips and JSON fidelity of the Postgres document collection."""

import pytest
from psycopg import sql
from typed_time_provider import Microseconds

from app.adapters.storage.postgres.postgres_document_collection_adapter import (
    PostgresDocumentCollectionAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.storage import CollectionIsolation
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import LlmTurnDocument, MessageDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.users import UserDocument
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.platform.strings import DatabaseUrl
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.builders import (
    COUNTRY_SAMPLES,
    CountrySample,
    build_business,
    build_knowledge_item,
    build_llm_turn,
    build_owner,
)
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import build_ticking_wall_clock

SAMPLE_IDS: list[str] = [sample.country_code for sample in COUNTRY_SAMPLES]


def read_row_metadata(
    connection_pool: PostgresConnectionPoolClient,
    table_name: str,
    document_key: str,
) -> tuple[str | None, int, int]:
    with connection_pool.transaction() as connection:
        connection.execute("select set_config('app.bypass_rls', 'on', true)")
        row = connection.execute(
            sql.SQL(
                "select business_id, created_at, updated_at from {} "
                "where document_key = %s"
            ).format(sql.Identifier("workshop", table_name)),
            (document_key,),
        ).fetchone()

    assert row is not None
    business_id: object = row[0]
    created_at: object = row[1]
    updated_at: object = row[2]
    assert business_id is None or isinstance(business_id, str)
    assert isinstance(created_at, int)
    assert isinstance(updated_at, int)
    return business_id, created_at, updated_at


@pytest.mark.parametrize("sample", COUNTRY_SAMPLES, ids=SAMPLE_IDS)
def test_business_round_trip_keeps_every_typed_value(
    postgres_collections: PostgresCollectionFactory,
    sample: CountrySample,
) -> None:
    businesses = postgres_collections(BusinessDocument, "businesses")
    business = build_business(sample, UserId())

    businesses.upsert(str(business.id), business)
    loaded = businesses.get(str(business.id))

    assert loaded == business
    assert loaded is not None
    assert loaded is not business
    assert type(loaded.id) is BusinessId
    assert type(loaded.name) is BusinessName
    assert type(loaded.currency_code) is CurrencyCode
    assert type(loaded.created_at) is Microseconds
    assert all(type(language) is LanguageTag for language in loaded.languages)
    assert loaded.model_dump_json() == business.model_dump_json()


@pytest.mark.parametrize("sample", COUNTRY_SAMPLES, ids=SAMPLE_IDS)
def test_knowledge_item_round_trip_in_any_script_and_currency(
    postgres_collections: PostgresCollectionFactory,
    sample: CountrySample,
) -> None:
    knowledge_items = postgres_collections(KnowledgeItemDocument, "knowledge_items")
    item = build_knowledge_item(sample, BusinessId())

    knowledge_items.upsert(str(item.id), item)
    loaded = knowledge_items.get(str(item.id))

    assert loaded == item
    assert loaded is not None
    assert type(loaded.title) is KnowledgeTitle
    assert loaded.title == sample.dish_title
    assert loaded.price_minor == sample.price_minor
    assert loaded.currency_code == sample.currency_code


def test_llm_turn_payload_is_stored_verbatim(
    postgres_collections: PostgresCollectionFactory,
) -> None:
    llm_turns = postgres_collections(LlmTurnDocument, "llm_turns")
    conversation_id = ConversationId()
    turns = [
        build_llm_turn(conversation_id, 0, "გამარჯობა! 🙂"),
        build_llm_turn(conversation_id, 1, "שלום, יש מקום להערב?"),
        build_llm_turn(conversation_id, 2, "مرحبا"),
    ]
    for turn in turns:
        llm_turns.upsert(str(turn.id), turn)

    loaded_turns = llm_turns.list_all()

    assert loaded_turns == turns
    assert [turn.payload for turn in loaded_turns] == [turn.payload for turn in turns]
    assert "\\u2028" in loaded_turns[0].payload


def test_large_integers_and_unicode_survive_jsonb(
    postgres_collections: PostgresCollectionFactory,
) -> None:
    messages = postgres_collections(MessageDocument, "messages")
    message = MessageDocument(
        conversation_id=ConversationId(),
        business_id=BusinessId(),
        direction=MessageDirection.INBOUND,
        author=MessageAuthor.CUSTOMER,
        text=MessageText('Line one\nline "two" \\ tab\t end — 𝔘𝔫𝔦𝔠𝔬𝔡𝔢 👨‍👩‍👧   ‏עברית‎'),
        cost_micro_usd=CostMicroUsd(9_007_199_254_740_993),
    )

    messages.upsert(str(message.id), message)
    loaded = messages.get(str(message.id))

    assert loaded == message
    assert loaded is not None
    assert loaded.cost_micro_usd == 9_007_199_254_740_993
    assert type(loaded.cost_micro_usd) is CostMicroUsd


def test_upsert_overwrites_and_keeps_first_write_time(
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    knowledge_items = PostgresCollectionFactory(
        connection_pool=connection_pool,
        storage_scope=StorageScopeContext(),
        wall_clock=build_ticking_wall_clock(step_microseconds=10),
    )(KnowledgeItemDocument, "knowledge_items")
    item = build_knowledge_item(COUNTRY_SAMPLES[0], BusinessId())
    knowledge_items.upsert(str(item.id), item)
    _, first_created_at, first_updated_at = read_row_metadata(
        connection_pool, "knowledge_items", str(item.id)
    )

    item.title = KnowledgeTitle("ხინკალი")
    knowledge_items.upsert(str(item.id), item)
    business_id, created_at, updated_at = read_row_metadata(
        connection_pool, "knowledge_items", str(item.id)
    )

    loaded = knowledge_items.get(str(item.id))
    assert loaded is not None
    assert loaded.title == "ხინკალი"
    assert len(knowledge_items.list_all()) == 1
    assert business_id == str(item.business_id)
    assert created_at == first_created_at
    assert updated_at > first_updated_at


def test_business_row_is_its_own_tenant_and_platform_rows_have_none(
    postgres_collections: PostgresCollectionFactory,
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    businesses = postgres_collections(BusinessDocument, "businesses")
    users = postgres_collections(UserDocument, "users")
    audit_log = postgres_collections(AuditLogEntryDocument, "audit_log_entries")
    owner = build_owner(COUNTRY_SAMPLES[0])
    business = build_business(COUNTRY_SAMPLES[0], owner.id)
    platform_entry = AuditLogEntryDocument(
        action=AuditAction.LOGIN,
        entity=AuditEntityName("user"),
    )

    businesses.upsert(str(business.id), business)
    users.upsert(str(owner.id), owner)
    audit_log.upsert(str(platform_entry.id), platform_entry)

    assert read_row_metadata(connection_pool, "businesses", str(business.id))[0] == (
        str(business.id)
    )
    assert read_row_metadata(connection_pool, "users", str(owner.id))[0] is None
    assert (
        read_row_metadata(connection_pool, "audit_log_entries", str(platform_entry.id))[
            0
        ]
        is None
    )


def test_list_all_keeps_first_write_order_and_delete_removes(
    postgres_collections: PostgresCollectionFactory,
) -> None:
    businesses = postgres_collections(BusinessDocument, "businesses")
    stored = [build_business(sample, UserId()) for sample in COUNTRY_SAMPLES]
    for business in stored:
        businesses.upsert(str(business.id), business)

    # Rewriting the first one does not move it to the end.
    stored[0].name = BusinessName("Renamed")
    businesses.upsert(str(stored[0].id), stored[0])
    businesses.delete(str(stored[2].id))
    businesses.delete("missing-key")

    loaded_ids = [business.id for business in businesses.list_all()]

    assert loaded_ids == [
        business.id for index, business in enumerate(stored) if index != 2
    ]
    assert businesses.get(str(stored[2].id)) is None
    assert businesses.get("missing-key") is None


def test_empty_collection_lists_nothing(
    postgres_collections: PostgresCollectionFactory,
) -> None:
    assert postgres_collections(UserDocument, "users").list_all() == []


def test_adapter_reports_name_and_isolation(
    postgres_collections: PostgresCollectionFactory,
) -> None:
    contacts = postgres_collections(KnowledgeItemDocument, "knowledge_items")
    users = postgres_collections(UserDocument, "users")

    assert contacts.collection_name == "knowledge_items"
    assert contacts.isolation is CollectionIsolation.TENANT
    assert users.isolation is CollectionIsolation.PLATFORM


def test_nul_character_is_rejected_with_a_clear_error(
    postgres_collections: PostgresCollectionFactory,
) -> None:
    knowledge_items = postgres_collections(KnowledgeItemDocument, "knowledge_items")
    item = build_knowledge_item(COUNTRY_SAMPLES[0], BusinessId())
    item.title = KnowledgeTitle("bad\x00title")

    with pytest.raises(ValidationFailedError, match="NUL"):
        knowledge_items.upsert(str(item.id), item)

    assert knowledge_items.list_all() == []


def test_missing_table_names_the_migration_command(
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    unknown_collection = PostgresCollectionFactory(
        connection_pool=connection_pool,
        storage_scope=StorageScopeContext(),
        wall_clock=build_ticking_wall_clock(),
    )(UserDocument, "not_migrated_yet")

    with pytest.raises(ExternalServiceError, match="migrate"):
        unknown_collection.list_all()

    with pytest.raises(ExternalServiceError, match="not_migrated_yet"):
        unknown_collection.upsert(str(UserId()), build_owner(COUNTRY_SAMPLES[1]))


def test_database_without_migrations_names_the_migration_command(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
) -> None:
    connection_pool = PostgresConnectionPoolClient(
        postgres_server.app_database_url(empty_database_name), max_size=1
    )
    try:
        users = PostgresCollectionFactory(
            connection_pool=connection_pool,
            storage_scope=StorageScopeContext(),
            wall_clock=build_ticking_wall_clock(),
        )(UserDocument, "users")

        with pytest.raises(ExternalServiceError, match="apply the migrations"):
            users.get("anything")
    finally:
        connection_pool.close()


def test_role_without_grants_gets_a_deployment_hint(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    with postgres_server.admin_connection(database_name) as connection:
        connection.execute("create role workshop_reader login")
    connection_pool = PostgresConnectionPoolClient(
        DatabaseUrl(postgres_server.conninfo(database_name, "workshop_reader")),
        max_size=1,
    )
    try:
        users = PostgresCollectionFactory(
            connection_pool=connection_pool,
            storage_scope=StorageScopeContext(),
            wall_clock=build_ticking_wall_clock(),
        )(UserDocument, "users")

        with pytest.raises(ExternalServiceError, match="grant it usage"):
            users.list_all()
    finally:
        connection_pool.close()
        with postgres_server.admin_connection(database_name) as connection:
            connection.execute("drop role workshop_reader")


def test_corrupted_row_fails_validation_instead_of_returning_garbage(
    postgres_collections: PostgresCollectionFactory,
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    users: PostgresDocumentCollectionAdapter[UserDocument] = postgres_collections(
        UserDocument, "users"
    )
    with connection_pool.transaction() as connection:
        connection.execute("select set_config('app.bypass_rls', 'on', true)")
        connection.execute(
            "insert into workshop.users "
            "(document_key, business_id, document, created_at, updated_at) "
            "values ('broken', null, '{\"locale\": 42}', 0, 0)"
        )

    with pytest.raises(ValueError, match="validation error"):
        users.get("broken")
