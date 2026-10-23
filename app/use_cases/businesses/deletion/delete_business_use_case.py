from typed_time_provider import Microseconds, WallClock

from app.contracts.business_erasure import (
    BusinessRowEraserAdapterContract,
    DeletionLedgerMirrorAdapterContract,
)
from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
    BusinessDeletionChange,
    BusinessDeletionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.business_closures import (
    BusinessClosureDocument,
    BusinessDeletionDocument,
    DeprovisionRecord,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.business_closures.business_deletions import (
    DeleteBusinessJobPayload,
)
from app.schemas.dto.business_closures.business_rows import BusinessTableRows
from app.schemas.dto.business_closures.deletion_ledger import DeletionLedgerRecord
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.privacy.constrained_integers import ProcessorErasureJobCount
from app.use_cases.businesses.deletion.business_deprovisioning import (
    BusinessDeprovisioner,
)
from app.use_cases.businesses.deletion.business_file_erasure import (
    BusinessFileEraser,
)
from app.use_cases.businesses.deletion.conversation_trace_erasure import (
    ConversationTraceEraser,
)
from app.use_cases.businesses.deletion.deletion_completion import DeletionCompletion
from app.use_cases.businesses.deletion.deletion_ledger_entries import (
    erasable_tables,
    new_ledger_entry,
    retained_counts,
    row_counts,
    stage_change,
)
from app.utilities.business_closures.retained_tables import QUEUED_JOBS_TABLE

# Rows written while the deletion ran (a job that was mid-way) are caught
# by counting again; three passes are plenty.
ERASE_PASSES: int = 3


class DeleteBusinessUseCase(UseCaseContract[QueuedJobInput, JobReport]):
    """
    Queued job "delete_business" (default lane, platform pool): a closed
    business whose 30 days are over is deleted for good, in stages the
    ledger entry records, so a retried job continues where the last attempt
    stopped and a concurrent one waits (one serial key per business):

    1. the ledger entry, mirrored outside the database before anything goes;
    2. the providers switched off (`BusinessDeprovisioner`);
    3. the business's queued jobs cleared, its model turns and vectors
       deleted and the sub-processors' erasure queued
       (`ConversationTraceEraser`);
    4. its files deleted (`BusinessFileEraser`);
    5. its rows counted and deleted in every table but what the law keeps
       (the audit log, issued invoices), the business's own row last, and
       counted again until nothing is left;
    6. the entry completed with its certificate's fingerprint, and the
       platform's audit chain recording the deletion with its counts
       (`DeletionCompletion`).

    A business whose closure was cancelled (or that has none) is not
    touched: the job ends without doing anything.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        closure_repo: BusinessClosureRepoContract,
        deletion_repo: BusinessDeletionRepoContract,
        ledger_mirror: DeletionLedgerMirrorAdapterContract,
        row_eraser: BusinessRowEraserAdapterContract,
        deprovisioner: BusinessDeprovisioner,
        trace_eraser: ConversationTraceEraser,
        file_eraser: BusinessFileEraser,
        completion: DeletionCompletion,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._closure_repo: BusinessClosureRepoContract = closure_repo
        self._deletion_repo: BusinessDeletionRepoContract = deletion_repo
        self._ledger_mirror: DeletionLedgerMirrorAdapterContract = ledger_mirror
        self._row_eraser: BusinessRowEraserAdapterContract = row_eraser
        self._deprovisioner: BusinessDeprovisioner = deprovisioner
        self._trace_eraser: ConversationTraceEraser = trace_eraser
        self._file_eraser: BusinessFileEraser = file_eraser
        self._completion: DeletionCompletion = completion
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: QueuedJobInput) -> JobReport:
        business_id: BusinessId = DeleteBusinessJobPayload.model_validate_json(
            str(input_data.payload)
        ).business_id
        entry: BusinessDeletionDocument | None = self._begin(business_id)
        if entry is None or entry.completed_at is not None:
            return JobReport(processed_count=ProcessedItemCount(0))

        self._ledger_mirror.record(
            DeletionLedgerRecord(
                business_id=business_id,
                deletion_id=entry.id,
                started_at=entry.started_at,
            )
        )
        entry = self._switch_off(entry, business_id)
        entry = self._clear_jobs(entry, business_id)
        if entry.files_erased_at is None:
            entry = self._advance(
                entry,
                stage_change(
                    erased_files=self._file_eraser.erase(business_id),
                    files_erased_at=self._now(),
                    updated_at=self._now(),
                ),
            )

        if entry.rows_counted_at is None:
            counts: list[BusinessTableRows] = self._row_eraser.count_rows(business_id)
            entry = self._advance(
                entry,
                stage_change(
                    erased_rows=row_counts(erasable_tables(counts)),
                    retained_rows=retained_counts(counts),
                    rows_counted_at=self._now(),
                    updated_at=self._now(),
                ),
            )

        self._completion.leave_brand(business_id, self._now())
        self._erase_rows(business_id)
        completed: BusinessDeletionDocument = self._completion.complete(
            entry, self._now()
        )
        return JobReport(
            processed_count=ProcessedItemCount(
                sum(int(item.row_count) for item in completed.erased_rows)
            )
        )

    def _begin(self, business_id: BusinessId) -> BusinessDeletionDocument | None:
        """The ledger entry of the deletion; None when the business is not due."""

        existing: BusinessDeletionDocument | None = (
            self._deletion_repo.find_by_business(business_id)
        )
        if existing is not None:
            return existing

        closure: BusinessClosureDocument | None = self._closure_repo.get(business_id)
        business: BusinessDocument | None = self._business_repo.get(business_id)
        if (
            closure is None
            or business is None
            or closure.cancelled_at is not None
            or closure.deletion_queued_at is None
        ):
            return None

        self._deletion_repo.begin(new_ledger_entry(business, closure, self._now()))
        return self._deletion_repo.find_by_business(business_id)

    def _switch_off(
        self, entry: BusinessDeletionDocument, business_id: BusinessId
    ) -> BusinessDeletionDocument:
        if entry.deprovisioned_at is not None:
            return entry

        records: list[DeprovisionRecord] = self._deprovisioner.deprovision(
            business_id, self._now()
        )
        return self._advance(
            entry,
            stage_change(
                deprovisioned=records,
                deprovisioned_at=self._now(),
                updated_at=self._now(),
            ),
        )

    def _clear_jobs(
        self, entry: BusinessDeletionDocument, business_id: BusinessId
    ) -> BusinessDeletionDocument:
        """
        The business's queued work goes (reminders, sends, exports); then the
        sub-processors' erasure is queued, so it is never deleted with it
        (a retry of this stage clears and queues both again).
        """

        if entry.jobs_cleared_at is not None:
            return entry

        self._row_eraser.erase_rows(business_id, [QUEUED_JOBS_TABLE])
        jobs: ProcessorErasureJobCount = self._trace_eraser.erase(business_id)
        return self._advance(
            entry,
            stage_change(
                processor_erasure_jobs=jobs,
                jobs_cleared_at=self._now(),
                updated_at=self._now(),
            ),
        )

    def _erase_rows(self, business_id: BusinessId) -> None:
        for _ in range(ERASE_PASSES):
            left: list[BusinessTableRows] = erasable_tables(
                self._row_eraser.count_rows(business_id)
            )
            if not left:
                return

            self._row_eraser.erase_rows(business_id, [count.table for count in left])

    def _advance(
        self, entry: BusinessDeletionDocument, change: BusinessDeletionChange
    ) -> BusinessDeletionDocument:
        advanced: BusinessDeletionDocument | None = self._deletion_repo.modify(
            entry.id, change
        )
        if advanced is None:
            raise ConflictError(f"The deletion ledger entry {entry.id} disappeared.")

        return advanced

    def _now(self) -> Microseconds:
        return self._wall_clock.now_unix()
