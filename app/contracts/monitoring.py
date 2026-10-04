"""
The platform's view of itself: the system page's indexed counts, the
activity the alerts measure, the shared signal counters, the alerts'
episodes, the recorded backups and drills, and the size of the database.
"""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.adapter_contract import AdapterContract
from app.contracts.repo_contract import RepoContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.monitoring import (
    MaintenanceRunKind,
    PlatformAlertCode,
    PlatformSignal,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.jobs import QueuedJobDocument, WorkerHeartbeatDocument
from app.schemas.domain.maintenance_runs import MaintenanceRunDocument
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.dto.admin_system import DeadJobTally
from app.schemas.dto.platform_alerts import SignalTally
from app.schemas.dto.platform_health import (
    ActivityWindow,
    DatabaseSize,
    JobStateTally,
    OutboundTally,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentQueryLimit,
)


class SystemHealthRepoContract(RepoContract, Protocol):
    """
    The admin system page's reads across every business (platform-wide),
    each an indexed count or a short indexed list.
    """

    def count_open_jobs(self) -> list[JobStateTally]:
        """Waiting, running and dead jobs by state and lane (no done ones)."""
        raise NotImplementedError

    def count_due_jobs(self, lane: JobLane, now: Microseconds) -> DocumentCount:
        """Waiting jobs of the lane whose time has come."""
        raise NotImplementedError

    def find_oldest_due_job(
        self, lane: JobLane, now: Microseconds
    ) -> QueuedJobDocument | None:
        raise NotImplementedError

    def count_dead_jobs_by_name(self) -> list[DeadJobTally]:
        raise NotImplementedError

    def list_pulses_since(self, since: Microseconds) -> list[WorkerHeartbeatDocument]:
        """Worker pulses written from `since` on, the freshest first."""
        raise NotImplementedError

    def count_channels_in_error(self) -> DocumentCount:
        raise NotImplementedError

    def list_channels_in_error(
        self, limit: DocumentQueryLimit
    ) -> list[ChannelDocument]:
        raise NotImplementedError

    def list_credentials_expiring_before(
        self, before: Microseconds, limit: DocumentQueryLimit
    ) -> list[ChannelDocument]:
        """Channels whose token runs out before then, soonest first."""
        raise NotImplementedError

    def list_active_channels(
        self, kinds: Sequence[ChannelKind], limit: DocumentQueryLimit
    ) -> list[ChannelDocument]:
        """Connected channels (and those in ERROR) of these kinds, any business."""
        raise NotImplementedError

    def get_businesses(
        self, business_ids: Sequence[BusinessId]
    ) -> list[BusinessDocument]:
        raise NotImplementedError


class PlatformActivityRepoContract(RepoContract, Protocol):
    """What the platform did in a window, counted across every business."""

    def count_handoffs(self, window: ActivityWindow) -> DocumentCount:
        """Handoffs created in the window, without the owners' test chats."""
        raise NotImplementedError

    def count_outbound(self, window: ActivityWindow) -> list[OutboundTally]:
        """Outbox messages queued in the window, by delivery state."""
        raise NotImplementedError

    def count_tool_error_messages(self, window: ActivityWindow) -> DocumentCount:
        """Messages written in the window with at least one failed tool call."""
        raise NotImplementedError


class PlatformAlertStateRepoContract(RepoContract, Protocol):
    def get_many(
        self, codes: Sequence[PlatformAlertCode]
    ) -> list[PlatformAlertStateDocument]:
        raise NotImplementedError

    def save(self, state: PlatformAlertStateDocument) -> None:
        raise NotImplementedError


class MaintenanceRunRepoContract(RepoContract, Protocol):
    def record(self, run: MaintenanceRunDocument) -> None:
        raise NotImplementedError

    def find_latest(self, kind: MaintenanceRunKind) -> MaintenanceRunDocument | None:
        """The run of this kind that finished last."""
        raise NotImplementedError


class SignalCounterAdapterContract(AdapterContract, Protocol):
    """
    Platform signals counted in fixed windows shared by every process (the
    rate-limit buckets: Postgres for all instances, memory without a
    database). Counting never raises: a lost count only weakens an alert.
    """

    def count(self, signal: PlatformSignal) -> None:
        raise NotImplementedError

    def read(self, signal: PlatformSignal, now: Microseconds) -> SignalTally:
        """The signal's events in the window holding `now` and the one before."""
        raise NotImplementedError


class DatabaseSizeAdapterContract(AdapterContract, Protocol):
    def measure(self) -> DatabaseSize | None:
        """The database's size by table from the catalog; None without Postgres."""
        raise NotImplementedError
