from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.monitoring import SystemHealthRepoContract
from app.repositories.document_queries import field_among, field_equals, time_range
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.jobs import QueuedJobDocument, WorkerHeartbeatDocument
from app.schemas.dto.admin_system import DeadJobTally
from app.schemas.dto.platform_health import JobStateTally
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_queries import DocumentFieldRange, DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.monitoring.constrained_integers import LaneJobCount
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentQueryLimit,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
KIND_FIELD: DocumentFieldPath = DocumentFieldPath("kind")
LANE_FIELD: DocumentFieldPath = DocumentFieldPath("lane")
NAME_FIELD: DocumentFieldPath = DocumentFieldPath("name")
RUN_AT_FIELD: DocumentFieldPath = DocumentFieldPath("run_at")
BEAT_AT_FIELD: DocumentFieldPath = DocumentFieldPath("beat_at")
CREDENTIAL_EXPIRES_AT_FIELD: DocumentFieldPath = DocumentFieldPath(
    "credential_expires_at"
)
# The states the system page counts; done and discarded jobs (most of the
# table until the purge) are left to the index.
OPEN_JOB_STATUSES: tuple[QueuedJobStatus, ...] = (
    QueuedJobStatus.PENDING,
    QueuedJobStatus.RUNNING,
    QueuedJobStatus.DEAD,
)
# Connected channels and those in ERROR (which still get every attempt).
ACTIVE_CHANNEL_STATUSES: tuple[ChannelStatus, ...] = (
    ChannelStatus.CONNECTED,
    ChannelStatus.ERROR,
)
MAX_WORKER_PULSES: DocumentQueryLimit = DocumentQueryLimit(50)
MICROSECOND: int = 1


class SystemHealthRepository(SystemHealthRepoContract):
    """
    The admin system page's reads, platform-wide: queued jobs by the plain
    columns of migration 1093 (doc_status, doc_lane, doc_run_at), worker
    pulses by beat_at, channels by status and token expiry (and the active
    Meta channels whose tokens the daily check asks about), and the
    businesses of a few channels by key.
    """

    def __init__(
        self,
        job_collection: DocumentCollectionAdapterContract[QueuedJobDocument],
        heartbeat_collection: DocumentCollectionAdapterContract[
            WorkerHeartbeatDocument
        ],
        channel_collection: DocumentCollectionAdapterContract[ChannelDocument],
        business_collection: DocumentCollectionAdapterContract[BusinessDocument],
    ) -> None:
        self._jobs: DocumentCollectionAdapterContract[QueuedJobDocument] = (
            job_collection
        )
        self._heartbeats: DocumentCollectionAdapterContract[WorkerHeartbeatDocument] = (
            heartbeat_collection
        )
        self._channels: DocumentCollectionAdapterContract[ChannelDocument] = (
            channel_collection
        )
        self._businesses: DocumentCollectionAdapterContract[BusinessDocument] = (
            business_collection
        )

    def count_open_jobs(self) -> list[JobStateTally]:
        groups: list[DocumentGroupCount] = self._jobs.count_by(
            DocumentAggregation(
                where=DocumentFilter(
                    among=(field_among(STATUS_FIELD, OPEN_JOB_STATUSES),)
                ),
                group_by=(STATUS_FIELD, LANE_FIELD),
            )
        )
        tallies: list[JobStateTally] = []
        for group in groups:
            status, lane = group.values
            if status is None or lane is None:
                continue

            tallies.append(
                JobStateTally(
                    status=QueuedJobStatus(str(status)),
                    lane=JobLane(str(lane)),
                    count=LaneJobCount(int(group.count)),
                )
            )

        return tallies

    def count_due_jobs(self, lane: JobLane, now: Microseconds) -> DocumentCount:
        return self._jobs.count_by_fields(
            [
                field_equals(STATUS_FIELD, QueuedJobStatus.PENDING),
                field_equals(LANE_FIELD, lane),
            ],
            within=due_by(now),
        )

    def find_oldest_due_job(
        self, lane: JobLane, now: Microseconds
    ) -> QueuedJobDocument | None:
        oldest: list[QueuedJobDocument] = self._jobs.list_by_range(
            due_by(now),
            matches=[
                field_equals(STATUS_FIELD, QueuedJobStatus.PENDING),
                field_equals(LANE_FIELD, lane),
            ],
            limit=DocumentQueryLimit(1),
        )
        return oldest[0] if oldest else None

    def count_dead_jobs_by_name(self) -> list[DeadJobTally]:
        groups: list[DocumentGroupCount] = self._jobs.count_by(
            DocumentAggregation(
                where=DocumentFilter(
                    matches=(field_equals(STATUS_FIELD, QueuedJobStatus.DEAD),)
                ),
                group_by=(NAME_FIELD,),
            )
        )
        tallies: list[DeadJobTally] = [
            DeadJobTally(name=JobName(str(name)), count=LaneJobCount(int(group.count)))
            for group in groups
            for name in group.values
            if name is not None
        ]
        return sorted(tallies, key=lambda tally: (-int(tally.count), str(tally.name)))

    def list_pulses_since(self, since: Microseconds) -> list[WorkerHeartbeatDocument]:
        return self._heartbeats.list_by_range(
            time_range(BEAT_AT_FIELD, starting_at=since),
            is_descending=True,
            limit=MAX_WORKER_PULSES,
        )

    def count_channels_in_error(self) -> DocumentCount:
        return self._channels.count_by_fields(
            [field_equals(STATUS_FIELD, ChannelStatus.ERROR)]
        )

    def list_channels_in_error(
        self, limit: DocumentQueryLimit
    ) -> list[ChannelDocument]:
        return self._channels.list_by_fields(
            [field_equals(STATUS_FIELD, ChannelStatus.ERROR)], limit=limit
        )

    def list_credentials_expiring_before(
        self, before: Microseconds, limit: DocumentQueryLimit
    ) -> list[ChannelDocument]:
        return self._channels.list_by_range(
            time_range(CREDENTIAL_EXPIRES_AT_FIELD, ending_before=before),
            limit=limit,
        )

    def list_active_channels(
        self, kinds: Sequence[ChannelKind], limit: DocumentQueryLimit
    ) -> list[ChannelDocument]:
        # The status index selects; the kind only narrows (a filter column).
        channels: list[ChannelDocument] = []
        for status in ACTIVE_CHANNEL_STATUSES:
            for kind in kinds:
                channels += self._channels.list_by_fields(
                    [
                        field_equals(STATUS_FIELD, status),
                        field_equals(KIND_FIELD, kind),
                    ],
                    limit=limit,
                )

        return channels[: int(limit)]

    def get_businesses(
        self, business_ids: Sequence[BusinessId]
    ) -> list[BusinessDocument]:
        if not business_ids:
            return []

        return self._businesses.get_many(
            [str(business_id) for business_id in business_ids]
        )


def due_by(now: Microseconds) -> DocumentFieldRange:
    """Jobs whose `run_at` has come (at or before `now`)."""

    return time_range(RUN_AT_FIELD, ending_before=Microseconds(int(now) + MICROSECOND))
