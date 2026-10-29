"""
The service level collections on Postgres (migration 1163): slots added by
two writers add up, windows and the newest row come from their indexes,
and the platform-wide sources count inbox events and reply latencies of
every business.
"""

import pytest
from typed_time_provider import Microseconds

from app.repositories.service_level_repositories import (
    ServiceLevelHourRepository,
    ServiceLevelSlotRepository,
    ServiceLevelSourceRepository,
)
from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.service_levels import (
    ServiceLevelHourDocument,
    ServiceLevelSlotDocument,
)
from app.schemas.typings.conversations.constrained_integers import (
    ReplyLatencyMilliseconds,
)
from app.schemas.typings.observability.constrained_integers import (
    ServiceLevelEventCount,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.utilities.client_health.reply_speed import REPLY_LATENCY_BUCKET_STARTS
from app.utilities.observability.service_levels import answer_p95, tally_answers
from tests.service_levels.sli_world import (
    HOUR,
    HOUR_START,
    MINUTE,
    SECOND,
    inbound,
    reply,
)
from tests.storage.conftest import PostgresCollectionFactory

# The sources span businesses: the test reads them platform-wide.
pytestmark = pytest.mark.usefixtures("platform_scope")

API: ServiceLevelSeries = ServiceLevelSeries.API_AVAILABILITY
INBOUND: ServiceLevelSeries = ServiceLevelSeries.INBOUND_ANSWERED
BUCKETS: tuple[ReplyLatencyMilliseconds, ...] = tuple(
    ReplyLatencyMilliseconds(start) for start in REPLY_LATENCY_BUCKET_STARTS
)


def count(value: int) -> ServiceLevelEventCount:
    return ServiceLevelEventCount(value)


def test_slots_add_up_and_are_read_by_series_and_window(
    postgres_collections: PostgresCollectionFactory,
) -> None:
    collection = postgres_collections(ServiceLevelSlotDocument, "service_level_slots")
    first_writer = ServiceLevelSlotRepository(collection)
    second_writer = ServiceLevelSlotRepository(collection)
    start = Microseconds(HOUR_START)

    first_writer.add(API, start, count(10), count(9))
    second_writer.add(API, start, count(5), count(5))
    first_writer.add(API, Microseconds(HOUR_START + 5 * MINUTE), count(1), count(1))
    first_writer.save(
        ServiceLevelSlotDocument(
            series=INBOUND, slot_start=start, total=count(4), good=count(3)
        )
    )

    window = first_writer.list_window(API, start, Microseconds(HOUR_START + 5 * MINUTE))
    assert [(int(slot.total), int(slot.good)) for slot in window] == [(15, 14)]
    latest = first_writer.find_latest(API)
    assert latest is not None
    assert int(latest.slot_start) == HOUR_START + 5 * MINUTE
    assert first_writer.find_latest(INBOUND) is not None

    removed = first_writer.delete_before(Microseconds(HOUR_START + MINUTE))

    assert int(removed) == 2
    assert first_writer.list_window(API, start, Microseconds(HOUR_START + HOUR)) != []


def test_hour_rows_are_read_since_and_newest_first(
    postgres_collections: PostgresCollectionFactory,
) -> None:
    hours = ServiceLevelHourRepository(
        postgres_collections(ServiceLevelHourDocument, "service_level_hours")
    )
    for offset in (2, 0, 1):
        hours.save(
            ServiceLevelHourDocument(
                hour_start=Microseconds(HOUR_START + offset * HOUR),
                api_requests=count(offset),
            )
        )

    since = hours.list_since(Microseconds(HOUR_START + HOUR))
    latest = hours.find_latest()

    assert [int(hour.api_requests) for hour in since] == [1, 2]
    assert latest is not None and int(latest.api_requests) == 2
    assert int(hours.delete_before(Microseconds(HOUR_START + HOUR))) == 1


def test_the_sources_count_every_business(
    postgres_collections: PostgresCollectionFactory,
) -> None:
    events = postgres_collections(InboundEventDocument, "inbound_events")
    messages = postgres_collections(MessageDocument, "messages")
    for event in (
        inbound(HOUR_START + MINUTE, 3 * SECOND),
        inbound(HOUR_START + 2 * MINUTE, 90 * SECOND),
        inbound(HOUR_START + 6 * MINUTE, 1 * SECOND),  # the next slot
    ):
        events.upsert(str(event.id), event)
    for message in (
        *(reply(HOUR_START + index * SECOND, 1_200) for index in range(19)),
        reply(HOUR_START + 30 * MINUTE, 70_000),
        reply(HOUR_START + 31 * MINUTE, None),
    ):
        messages.upsert(str(message.id), message)
    sources = ServiceLevelSourceRepository(events, messages)

    slot = sources.list_inbound_events(
        Microseconds(HOUR_START),
        Microseconds(HOUR_START + 5 * MINUTE),
        DocumentQueryLimit(100),
    )
    latencies = sources.count_reply_latencies(
        Microseconds(HOUR_START), Microseconds(HOUR_START + HOUR), BUCKETS
    )

    total, good = tally_answers(slot)
    assert (int(total), int(good)) == (2, 1)
    assert sum(int(tally.count) for tally in latencies) == 20
    p95 = answer_p95(latencies)
    assert p95 is not None and 1_000 <= int(p95) <= 90_000
