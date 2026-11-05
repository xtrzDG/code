from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.analytics_repositories import (
    ProductEventRepoContract,
    WebVitalSampleRepoContract,
)
from app.repositories.aggregate_reading import parse_choice
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    field_equals,
    of_business,
    time_range,
)
from app.schemas.constants.analytics import (
    DeviceClass,
    ProductEventName,
    WebVitalName,
)
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.domain.web_vitals import WebVitalSampleDocument
from app.schemas.dto.analytics.web_vital_counts import WebVitalBucketCount
from app.schemas.dto.storage_aggregates import (
    DocumentAggregation,
    DocumentFieldBuckets,
    DocumentGroupCount,
)
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.analytics.constrained_integers import (
    WebVitalSampleCount,
    WebVitalValue,
)
from app.schemas.typings.analytics.constrained_strings import CabinetRoutePattern
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.storage.constrained_integers import (
    DocumentBucketIndex,
    DocumentCount,
    DocumentQueryLimit,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger

NAME_FIELD: DocumentFieldPath = DocumentFieldPath("name")
OCCURRED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("occurred_at")
METRIC_FIELD: DocumentFieldPath = DocumentFieldPath("metric")
ROUTE_FIELD: DocumentFieldPath = DocumentFieldPath("route")
DEVICE_CLASS_FIELD: DocumentFieldPath = DocumentFieldPath("device_class")
VALUE_FIELD: DocumentFieldPath = DocumentFieldPath("value")


class ProductEventRepository(ProductEventRepoContract):
    """
    The owners' product events (platform-wide), keyed by event id; read by
    name within a time range (indexed, migration 1074).
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[ProductEventDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[ProductEventDocument] = (
            collection
        )

    def record(self, event: ProductEventDocument) -> IsDocumentInserted:
        return self._collection.insert_if_absent(str(event.id), event)

    def list_named(
        self,
        names: Sequence[ProductEventName],
        occurred_from: Microseconds | None,
        occurred_before: Microseconds,
    ) -> list[ProductEventDocument]:
        events: list[ProductEventDocument] = []
        for name in dict.fromkeys(names):
            events.extend(
                self._collection.list_by_range(
                    time_range(
                        OCCURRED_AT_FIELD,
                        starting_at=occurred_from,
                        ending_before=occurred_before,
                    ),
                    matches=(field_equals(NAME_FIELD, name),),
                )
            )

        return sorted(events, key=lambda event: (int(event.occurred_at), event.id))

    def list_by_business(
        self, business_id: BusinessId, limit: DocumentQueryLimit
    ) -> list[ProductEventDocument]:
        return self._collection.list_by_fields((of_business(business_id),), limit=limit)


class WebVitalSampleRepository(WebVitalSampleRepoContract):
    """
    Web Vital samples (platform-wide), counted per vital and period by the
    database and purged by age (indexed, migration 1074).
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[WebVitalSampleDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[WebVitalSampleDocument] = (
            collection
        )

    def add_many(self, samples: Sequence[WebVitalSampleDocument]) -> None:
        self._collection.upsert_many([(str(sample.id), sample) for sample in samples])

    def count_buckets(
        self,
        metric: WebVitalName,
        recorded_from: Microseconds,
        recorded_before: Microseconds,
        bucket_starts: Sequence[WebVitalValue],
    ) -> list[WebVitalBucketCount]:
        groups: list[DocumentGroupCount] = self._collection.count_by(
            DocumentAggregation(
                where=DocumentFilter(
                    matches=(field_equals(METRIC_FIELD, metric),),
                    ranges=(
                        time_range(
                            CREATED_AT_FIELD,
                            starting_at=recorded_from,
                            ending_before=recorded_before,
                        ),
                    ),
                ),
                group_by=(ROUTE_FIELD, DEVICE_CLASS_FIELD),
                buckets=DocumentFieldBuckets(
                    field=VALUE_FIELD,
                    starts=tuple(
                        DocumentFieldInteger(int(start)) for start in bucket_starts
                    ),
                ),
            )
        )
        return [
            count for group in groups if (count := read_bucket_count(group)) is not None
        ]

    def delete_recorded_before(self, cutoff: Microseconds) -> DocumentCount:
        return self._collection.delete_by_range(
            time_range(CREATED_AT_FIELD, ending_before=cutoff)
        )


def read_bucket_count(group: DocumentGroupCount) -> WebVitalBucketCount | None:
    """
    One group as a typed count; None for a value this release cannot read
    (a route or device written by a newer release during a deploy).
    """

    route_text, device_text = group.values
    device_class: DeviceClass | None = parse_choice(DeviceClass, device_text)
    if route_text is None or device_class is None or group.bucket is None:
        return None

    try:
        route = CabinetRoutePattern(str(route_text))
    except ValueError:
        return None

    return WebVitalBucketCount(
        route=route,
        device_class=device_class,
        bucket=DocumentBucketIndex(int(group.bucket)),
        count=WebVitalSampleCount(int(group.count)),
    )
