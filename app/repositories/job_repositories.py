from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.jobs import QueuedJobRepoContract
from app.schemas.constants.jobs import QueuedJobStatus
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.typings.platform.prefixed_id import QueuedJobId


class QueuedJobRepository(QueuedJobRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[QueuedJobDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[QueuedJobDocument] = (
            collection
        )

    def save(self, job: QueuedJobDocument) -> None:
        self._collection.upsert(str(job.id), job)

    def get(self, job_id: QueuedJobId) -> QueuedJobDocument | None:
        return self._collection.get(str(job_id))

    def list_due(self, now: Microseconds) -> list[QueuedJobDocument]:
        due_jobs: list[QueuedJobDocument] = [
            job
            for job in self._collection.list_all()
            if job.status is QueuedJobStatus.PENDING and job.run_at <= now
        ]
        return sorted(due_jobs, key=lambda job: job.run_at)
