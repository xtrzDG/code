"""
A repository call on Postgres is a span (with tracing on): the statement's
operation and table, never its parameters; the pool's metrics see the
connection taken and returned.
"""

from collections.abc import Iterator

import pytest
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import SpanKind as OtelSpanKind
from prometheus_client import CollectorRegistry
from typed_time_provider import Microseconds

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.containers.telemetry_factories import build_pool_instruments
from app.repositories.conversation_repositories import ConversationRepository
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.observability.metrics.prometheus_service_metrics import (
    PrometheusServiceMetrics,
)
from app.utilities.observability.tracing.open_telemetry_setup import (
    INSTRUMENTATION_NAME,
)
from app.utilities.observability.tracing.open_telemetry_span_tracer import (
    OpenTelemetrySpanTracer,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.storage_testing import build_fixed_wall_clock

CUSTOMER_HANDLE: str = "visitor-secret-handle-0001"
START: int = 1_790_000_000_000_000


@pytest.fixture
def exporter() -> InMemorySpanExporter:
    return InMemorySpanExporter()


@pytest.fixture
def registry() -> CollectorRegistry:
    return CollectorRegistry()


@pytest.fixture
def traced_pool(
    database_url: DatabaseUrl,
    exporter: InMemorySpanExporter,
    registry: CollectorRegistry,
) -> Iterator[PostgresConnectionPoolClient]:
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    instruments = build_pool_instruments(
        PrometheusServiceMetrics(registry),
        OpenTelemetrySpanTracer(provider.get_tracer(INSTRUMENTATION_NAME)),
    )
    pool = PostgresConnectionPoolClient(
        database_url, max_size=2, instruments=instruments
    )
    try:
        yield pool
    finally:
        pool.close()
        provider.shutdown()


def database_spans(exporter: InMemorySpanExporter) -> list[ReadableSpan]:
    return [
        span
        for span in exporter.get_finished_spans()
        if span.attributes is not None
        and span.attributes.get("db.system") == "postgresql"
    ]


def test_a_repository_read_is_a_span_without_its_parameters(
    traced_pool: PostgresConnectionPoolClient,
    exporter: InMemorySpanExporter,
    registry: CollectorRegistry,
) -> None:
    storage_scope = StorageScopeContext()
    collections = PostgresCollectionFactory(
        traced_pool, storage_scope, build_fixed_wall_clock()
    )
    conversations = ConversationRepository(
        collections(ConversationDocument, "conversations")
    )
    business_id = BusinessId()
    conversation = ConversationDocument(
        business_id=business_id,
        contact_id=ContactId(),
        assistant_version_id=AssistantVersionId(),
        channel=ChannelKind.WEB_CHAT,
        channel_user_id=ChannelUserId(CUSTOMER_HANDLE),
        last_message_at=Microseconds(START),
        created_at=Microseconds(START),
        updated_at=Microseconds(START),
    )
    with storage_scope.scoped_to_business(business_id):
        conversations.save(conversation)
        exporter.clear()
        found = conversations.get(business_id, conversation.id)

    assert found is not None
    spans = database_spans(exporter)
    reads = [span for span in spans if span.name == "SELECT conversations"]
    assert reads, [span.name for span in spans]
    read = reads[0]
    assert read.kind is OtelSpanKind.CLIENT
    assert read.attributes is not None
    assert read.attributes["db.operation.name"] == "SELECT"
    assert read.attributes["db.collection.name"] == "conversations"
    recorded: str = " ".join(
        f"{span.name} {dict(span.attributes or {})}" for span in spans
    )
    assert str(conversation.id) not in recorded
    assert str(business_id) not in recorded
    assert CUSTOMER_HANDLE not in recorded
    assert registry.get_sample_value("workshop_db_pool_connections_in_use") == 0
    assert (registry.get_sample_value("workshop_db_pool_wait_seconds_count") or 0) > 0
