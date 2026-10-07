"""
Fakes for the outbox's queuing steps: a job queue that records what it was
asked to queue (or refuses), a unit of work that records its outcome, and
an outbox whose stored row can go missing between insert and read.
"""

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.storage import StorageUnitOfWorkContract
from app.repositories.delivery_repositories import OutboundMessageRepository
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deliveries.prefixed_id import OutboundMessageId
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.schemas.typings.storage.booleans import IsDocumentInserted


class RecordingUnitOfWork(StorageUnitOfWorkContract):
    """
    Records how each unit ended ("commit" or "rollback") and how deep the
    code runs in units right now, so a test sees which writes share one.
    """

    def __init__(self) -> None:
        self.outcomes: list[str] = []
        self.depth: int = 0

    @contextmanager
    def unit_of_work(self) -> Generator[None]:
        self.depth += 1
        try:
            yield
        except BaseException:
            self.outcomes.append("rollback")
            raise
        else:
            self.outcomes.append("commit")
        finally:
            self.depth -= 1


@dataclass(frozen=True)
class QueuedCall:
    job_name: JobName
    payload: JobPayloadJson
    business_id: BusinessId | None
    run_at: Microseconds | None
    lane: JobLane
    serial_key: JobSerialKey | None
    unit_depth: int


class RecordingJobQueue(JobQueueFacilitatorContract):
    """Records every job it is asked to queue; refuses all with `failure`."""

    def __init__(
        self,
        unit_of_work: RecordingUnitOfWork | None = None,
        failure: Exception | None = None,
    ) -> None:
        self.calls: list[QueuedCall] = []
        self._unit_of_work: RecordingUnitOfWork | None = unit_of_work
        self._failure: Exception | None = failure

    def enqueue(
        self,
        job_name: JobName,
        payload: JobPayloadJson,
        business_id: BusinessId | None,
        run_at: Microseconds | None = None,
        lane: JobLane = JobLane.DEFAULT,
        serial_key: JobSerialKey | None = None,
    ) -> QueuedJobId:
        if self._failure is not None:
            raise self._failure

        depth: int = 0 if self._unit_of_work is None else self._unit_of_work.depth
        self.calls.append(
            QueuedCall(job_name, payload, business_id, run_at, lane, serial_key, depth)
        )
        return QueuedJobId()


class RecordingOutbox(OutboundMessageRepository):
    """The in-memory outbox, noting the unit depth of every insert."""

    def __init__(self, unit_of_work: RecordingUnitOfWork | None = None) -> None:
        super().__init__(
            InMemoryDocumentCollectionAdapter[OutboundMessageDocument](
                OutboundMessageDocument
            )
        )
        self.insert_depths: list[int] = []
        self._unit_of_work: RecordingUnitOfWork | None = unit_of_work

    def insert_if_new(self, message: OutboundMessageDocument) -> IsDocumentInserted:
        self.insert_depths.append(
            0 if self._unit_of_work is None else self._unit_of_work.depth
        )
        return super().insert_if_new(message)

    def upsert_for_test(self, message: OutboundMessageDocument) -> None:
        """Overwrite a stored message (its delivery state moved on)."""

        self._collection.upsert(str(message.id), message)


class VanishingOutbox(RecordingOutbox):
    """Every key was taken already, yet the row cannot be read back (purged)."""

    def insert_if_new(self, message: OutboundMessageDocument) -> IsDocumentInserted:
        del message
        return IsDocumentInserted(False)

    def get(
        self, business_id: BusinessId, message_id: OutboundMessageId
    ) -> OutboundMessageDocument | None:
        del business_id, message_id
        return None
