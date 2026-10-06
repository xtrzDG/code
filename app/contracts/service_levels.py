"""
The service level indicators (docs/operations/slo.md): the shared
five-minute slots, the hourly rows, and the platform-wide reads they are
computed from.
"""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.service_levels import (
    ServiceLevelHourDocument,
    ServiceLevelSlotDocument,
)
from app.schemas.dto.service_levels import LatencyBucketTally
from app.schemas.typings.conversations.constrained_integers import (
    ReplyLatencyMilliseconds,
)
from app.schemas.typings.observability.constrained_integers import (
    ServiceLevelEventCount,
)
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentQueryLimit,
)


class ServiceLevelSlotRepoContract(RepoContract, Protocol):
    def add(
        self,
        series: ServiceLevelSeries,
        slot_start: Microseconds,
        total: ServiceLevelEventCount,
        good: ServiceLevelEventCount,
    ) -> None:
        """
        Add events to a slot, in one atomic step per slot: several API
        processes add to the same slot.
        """
        raise NotImplementedError

    def save(self, slot: ServiceLevelSlotDocument) -> None:
        """Store a slot counted in one go (a rerun writes the same counts)."""
        raise NotImplementedError

    def list_window(
        self, series: ServiceLevelSeries, since: Microseconds, until: Microseconds
    ) -> list[ServiceLevelSlotDocument]:
        """The series' slots starting from `since` up to `until` (exclusive)."""
        raise NotImplementedError

    def find_latest(
        self, series: ServiceLevelSeries
    ) -> ServiceLevelSlotDocument | None:
        raise NotImplementedError

    def delete_before(self, before: Microseconds) -> DocumentCount:
        """Remove every series' slots that started before `before`."""
        raise NotImplementedError


class ServiceLevelHourRepoContract(RepoContract, Protocol):
    def save(self, hour: ServiceLevelHourDocument) -> None:
        raise NotImplementedError

    def list_since(self, since: Microseconds) -> list[ServiceLevelHourDocument]:
        """The rows of the hours from `since` on, the oldest first."""
        raise NotImplementedError

    def find_latest(self) -> ServiceLevelHourDocument | None:
        raise NotImplementedError

    def delete_before(self, before: Microseconds) -> DocumentCount:
        raise NotImplementedError


class ServiceLevelSourceRepoContract(RepoContract, Protocol):
    """What the SLIs are computed from, read across every business."""

    def list_inbound_events(
        self, since: Microseconds, until: Microseconds, limit: DocumentQueryLimit
    ) -> list[InboundEventDocument]:
        """The inbox events received in the window (created_at index)."""
        raise NotImplementedError

    def count_reply_latencies(
        self,
        since: Microseconds,
        until: Microseconds,
        bucket_starts: Sequence[ReplyLatencyMilliseconds],
    ) -> list[LatencyBucketTally]:
        """
        The assistant replies of the window with a measured wait, counted
        per latency bucket by the database.
        """
        raise NotImplementedError
