"""Readiness of the API: the database probe and the background worker pulse."""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.adapter_contract import AdapterContract
from app.contracts.repo_contract import RepoContract
from app.contracts.utility_contract import UtilityContract
from app.schemas.domain.jobs import WorkerHeartbeatDocument
from app.schemas.dto.health import DatabaseProbe
from app.schemas.typings.storage.constrained_integers import DocumentCount


class DatabaseProbeAdapterContract(AdapterContract, Protocol):
    def probe(self) -> DatabaseProbe:
        """
        Borrow a connection, run `select 1` and read the applied migrations,
        all within the probe's timeout. Never raises: a failure is reported
        in the result.
        """
        raise NotImplementedError


class WorkerHeartbeatRepoContract(RepoContract, Protocol):
    """The pulses of background worker processes (a platform collection)."""

    def save(self, heartbeat: WorkerHeartbeatDocument) -> None:
        raise NotImplementedError

    def find_freshest(self) -> WorkerHeartbeatDocument | None:
        """The most recently written pulse of any worker, or None."""
        raise NotImplementedError

    def delete_beaten_before(self, beaten_before: Microseconds) -> DocumentCount:
        """Delete the pulses last written before `beaten_before`; how many."""
        raise NotImplementedError


class ReadinessMemoryContract(UtilityContract, Protocol):
    """
    What the readiness check of one process remembers between probes: since
    when its pool has been exhausted, and whether every migration of this
    build was applied the last time that could be read.
    """

    def note_pool(self, is_exhausted: bool, now: Microseconds) -> Microseconds | None:
        """
        Record this probe's pool state; while exhausted, the start of the
        unbroken run of exhausted probes (None once a connection came free).
        """
        raise NotImplementedError

    def note_migrations(self, are_applied: bool) -> None:
        raise NotImplementedError

    def were_migrations_applied(self) -> bool | None:
        """The last reading (None before the first one)."""
        raise NotImplementedError
