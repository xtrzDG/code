"""
What the platform's own stores report for the system page and the alerts:
queued jobs counted by state and lane, the size of the database, and the
platform's activity counted over a stretch of time.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.dto.admin_system import TableSizeView
from app.schemas.typings.monitoring.constrained_integers import (
    LaneJobCount,
    StorageByteSize,
)
from app.schemas.typings.storage.constrained_integers import DocumentCount


class JobStateTally(ImmutableDTO):
    """How many queued jobs of one lane are in one state."""

    status: QueuedJobStatus
    lane: JobLane
    count: LaneJobCount


class DatabaseSize(ImmutableDTO):
    """The disk space of the whole database and of each application table."""

    total_bytes: StorageByteSize
    tables: list[TableSizeView]


class ActivityWindow(ImmutableDTO):
    """A stretch of time, from `since` (inclusive) to `until` (exclusive)."""

    since: Microseconds
    until: Microseconds


class OutboundTally(ImmutableDTO):
    """How many outbox messages queued in a window ended in one state."""

    status: OutboundMessageStatus
    count: DocumentCount
