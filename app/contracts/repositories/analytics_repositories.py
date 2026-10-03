"""
Persistence contracts of the founder's growth analytics: the owners'
product events and the cabinet's Web Vitals. Both are platform-wide (a
sign-in names no business; the metrics read every business).
"""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.constants.analytics import ProductEventName, WebVitalName
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.domain.web_vitals import WebVitalSampleDocument
from app.schemas.dto.analytics.web_vital_counts import WebVitalBucketCount
from app.schemas.typings.analytics.constrained_integers import WebVitalValue
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.storage.constrained_integers import DocumentCount


class ProductEventRepoContract(RepoContract, Protocol):
    def record(self, event: ProductEventDocument) -> IsDocumentInserted:
        """
        Store the event; one whose id is taken already (a once-only step
        recorded again, also by another process) changes nothing. True when
        it was new.
        """
        raise NotImplementedError

    def list_named(
        self,
        names: Sequence[ProductEventName],
        occurred_from: Microseconds | None,
        occurred_before: Microseconds,
    ) -> list[ProductEventDocument]:
        """
        The events of these names that happened from `occurred_from` (from
        the beginning when None) until before `occurred_before`, oldest
        first (indexed by name and time).
        """
        raise NotImplementedError


class WebVitalSampleRepoContract(RepoContract, Protocol):
    def add_many(self, samples: Sequence[WebVitalSampleDocument]) -> None:
        """Store one reported batch in one write."""
        raise NotImplementedError

    def count_buckets(
        self,
        metric: WebVitalName,
        recorded_from: Microseconds,
        recorded_before: Microseconds,
        bucket_starts: Sequence[WebVitalValue],
    ) -> list[WebVitalBucketCount]:
        """
        Samples of one vital recorded in the period, counted per route,
        device class and value bucket by the database (no sample is read).
        """
        raise NotImplementedError

    def delete_recorded_before(self, cutoff: Microseconds) -> DocumentCount:
        """Delete the samples recorded before `cutoff`; how many."""
        raise NotImplementedError
