"""
The service level indicators as stored (platform collections, 1163) and
the platform-wide reads they are computed from.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.service_levels import (
    ServiceLevelHourRepoContract,
    ServiceLevelSlotRepoContract,
    ServiceLevelSourceRepoContract,
)
from app.repositories.conversation_lookup_fields import AUTHOR_FIELD
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    field_equals,
    time_range,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.service_levels import (
    ServiceLevelHourDocument,
    ServiceLevelSlotDocument,
)
from app.schemas.dto.service_levels import LatencyBucketTally
from app.schemas.dto.storage_aggregates import (
    DocumentAggregation,
    DocumentFieldBuckets,
    DocumentGroupCount,
)
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.client_health.constrained_integers import (
    MeasuredReplyCount,
)
from app.schemas.typings.conversations.constrained_integers import (
    ReplyLatencyMilliseconds,
)
from app.schemas.typings.observability.constrained_integers import (
    ServiceLevelEventCount,
)
from app.schemas.typings.storage.constrained_integers import (
    DocumentBucketIndex,
    DocumentCount,
    DocumentQueryLimit,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.utilities.observability.service_levels import slot_key

SERIES_FIELD: DocumentFieldPath = DocumentFieldPath("series")
SLOT_START_FIELD: DocumentFieldPath = DocumentFieldPath("slot_start")
HOUR_START_FIELD: DocumentFieldPath = DocumentFieldPath("hour_start")
REPLY_LATENCY_FIELD: DocumentFieldPath = DocumentFieldPath("reply_latency_ms")
ONE: DocumentQueryLimit = DocumentQueryLimit(1)
BEGINNING: Microseconds = Microseconds(0)


class ServiceLevelSlotRepository(ServiceLevelSlotRepoContract):
    """
    Five-minute slots keyed `<series>:<slot_start>`, read by the series'
    index `(doc_series, doc_slot_start)`. Adding is an insert of a new slot
    or, when another process created it first, an atomic modify.
    """

    def __init__(
        self, collection: DocumentCollectionAdapterContract[ServiceLevelSlotDocument]
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            ServiceLevelSlotDocument
        ] = collection

    def add(
        self,
        series: ServiceLevelSeries,
        slot_start: Microseconds,
        total: ServiceLevelEventCount,
        good: ServiceLevelEventCount,
    ) -> None:
        key: str = slot_key(series, slot_start)
        fresh = ServiceLevelSlotDocument(
            series=series, slot_start=slot_start, total=total, good=good
        )
        if self._collection.insert_if_absent(key, fresh):
            return

        def add_to(slot: ServiceLevelSlotDocument) -> ServiceLevelSlotDocument:
            slot.total = ServiceLevelEventCount(int(slot.total) + int(total))
            slot.good = ServiceLevelEventCount(int(slot.good) + int(good))
            return slot

        self._collection.modify(key, add_to)

    def save(self, slot: ServiceLevelSlotDocument) -> None:
        self._collection.upsert(slot_key(slot.series, slot.slot_start), slot)

    def list_window(
        self, series: ServiceLevelSeries, since: Microseconds, until: Microseconds
    ) -> list[ServiceLevelSlotDocument]:
        return self._collection.list_by_range(
            time_range(SLOT_START_FIELD, starting_at=since, ending_before=until),
            matches=[field_equals(SERIES_FIELD, series)],
        )

    def find_latest(
        self, series: ServiceLevelSeries
    ) -> ServiceLevelSlotDocument | None:
        latest: list[ServiceLevelSlotDocument] = self._collection.list_by_range(
            time_range(SLOT_START_FIELD, starting_at=BEGINNING),
            matches=[field_equals(SERIES_FIELD, series)],
            is_descending=True,
            limit=ONE,
        )
        return latest[0] if latest else None

    def delete_before(self, before: Microseconds) -> DocumentCount:
        return DocumentCount(
            sum(
                int(
                    self._collection.delete_by_range(
                        time_range(SLOT_START_FIELD, ending_before=before),
                        matches=[field_equals(SERIES_FIELD, series)],
                    )
                )
                for series in ServiceLevelSeries
            )
        )


class ServiceLevelHourRepository(ServiceLevelHourRepoContract):
    """One row per hour keyed by its start, read by `doc_hour_start`."""

    def __init__(
        self, collection: DocumentCollectionAdapterContract[ServiceLevelHourDocument]
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            ServiceLevelHourDocument
        ] = collection

    def save(self, hour: ServiceLevelHourDocument) -> None:
        self._collection.upsert(str(int(hour.hour_start)), hour)

    def list_since(self, since: Microseconds) -> list[ServiceLevelHourDocument]:
        return self._collection.list_by_range(
            time_range(HOUR_START_FIELD, starting_at=since)
        )

    def find_latest(self) -> ServiceLevelHourDocument | None:
        latest: list[ServiceLevelHourDocument] = self._collection.list_by_range(
            time_range(HOUR_START_FIELD, starting_at=BEGINNING),
            is_descending=True,
            limit=ONE,
        )
        return latest[0] if latest else None

    def delete_before(self, before: Microseconds) -> DocumentCount:
        return self._collection.delete_by_range(
            time_range(HOUR_START_FIELD, ending_before=before)
        )


class ServiceLevelSourceRepository(ServiceLevelSourceRepoContract):
    """
    Platform-wide reads (a platform operator's scope): the inbox events of
    a slot by `inbound_events_doc_created_at_idx` (1020), and the assistant
    replies of an hour per latency bucket by
    `messages_doc_platform_reply_latency_idx` (1163), counted by the
    database. Only the counts leave this repository's callers.
    """

    def __init__(
        self,
        inbound_event_collection: DocumentCollectionAdapterContract[
            InboundEventDocument
        ],
        message_collection: DocumentCollectionAdapterContract[MessageDocument],
    ) -> None:
        self._events: DocumentCollectionAdapterContract[InboundEventDocument] = (
            inbound_event_collection
        )
        self._messages: DocumentCollectionAdapterContract[MessageDocument] = (
            message_collection
        )

    def list_inbound_events(
        self, since: Microseconds, until: Microseconds, limit: DocumentQueryLimit
    ) -> list[InboundEventDocument]:
        return self._events.list_by_range(
            time_range(CREATED_AT_FIELD, starting_at=since, ending_before=until),
            limit=limit,
        )

    def count_reply_latencies(
        self,
        since: Microseconds,
        until: Microseconds,
        bucket_starts: Sequence[ReplyLatencyMilliseconds],
    ) -> list[LatencyBucketTally]:
        groups: list[DocumentGroupCount] = self._messages.count_by(
            DocumentAggregation(
                where=DocumentFilter(
                    matches=(field_equals(AUTHOR_FIELD, MessageAuthor.ASSISTANT),),
                    ranges=(
                        time_range(
                            CREATED_AT_FIELD, starting_at=since, ending_before=until
                        ),
                    ),
                ),
                buckets=DocumentFieldBuckets(
                    field=REPLY_LATENCY_FIELD,
                    starts=tuple(
                        DocumentFieldInteger(int(start)) for start in bucket_starts
                    ),
                ),
            )
        )
        return [
            LatencyBucketTally(
                bucket=DocumentBucketIndex(int(group.bucket)),
                count=MeasuredReplyCount(int(group.count)),
            )
            for group in groups
            if group.bucket is not None
        ]
