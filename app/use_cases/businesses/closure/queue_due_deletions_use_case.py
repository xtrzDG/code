from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract, QueuedJobRepoContract
from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.business_closures import BusinessClosureDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.strings import JobPayloadJson
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.utilities.business_closures.deletion_jobs import (
    DELETE_BUSINESS_JOB,
    deletion_payload,
    deletion_serial_key,
)

PAGE: DocumentQueryLimit = DocumentQueryLimit(100)


class QueueDueDeletionsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Hourly, across businesses (`queue_business_deletions`): every closure
    whose 30 days are over is marked `deletion_queued_at` (in one step that
    skips a closure being cancelled, so a cancel and the deletion never
    both win) and gets its `delete_business` job on the default lane, run
    through the platform pool. A closure whose job is still waiting or
    running gets no second one; one whose job died (a release that did not
    know the job, retries run out) gets a new one, so a deletion is never
    lost. The deletion removes the closure with the rest of the business.
    """

    def __init__(
        self,
        closure_repo: BusinessClosureRepoContract,
        job_queue: JobQueueFacilitatorContract,
        job_repo: QueuedJobRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._closure_repo: BusinessClosureRepoContract = closure_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._job_repo: QueuedJobRepoContract = job_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        queued: int = 0
        after: BusinessClosureDocument | None = None
        while True:
            page: list[BusinessClosureDocument] = self._closure_repo.page_due(
                now, after, PAGE
            )
            queued += sum(1 for closure in page if self._queue(closure, now))
            if len(page) < int(PAGE):
                return JobReport(processed_count=ProcessedItemCount(queued))

            after = page[-1]

    def _queue(self, closure: BusinessClosureDocument, now: Microseconds) -> bool:
        def mark(current: BusinessClosureDocument) -> BusinessClosureDocument | None:
            if current.cancelled_at is not None:
                return None

            if current.deletion_queued_at is None:
                current.deletion_queued_at = now
                current.updated_at = now
            return current

        if self._closure_repo.modify(closure.business_id, mark) is None:
            return False

        payload: JobPayloadJson = deletion_payload(closure.business_id)
        if self._job_repo.list_active_payloads(DELETE_BUSINESS_JOB, [payload]):
            return False

        self._job_queue.enqueue(
            DELETE_BUSINESS_JOB,
            payload,
            business_id=None,
            lane=JobLane.DEFAULT,
            serial_key=deletion_serial_key(closure.business_id),
        )
        return True
