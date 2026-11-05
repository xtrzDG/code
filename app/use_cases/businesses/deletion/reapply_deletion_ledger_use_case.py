import logging

from app.contracts.business_erasure import (
    BusinessRowEraserAdapterContract,
    DeletionLedgerMirrorAdapterContract,
)
from app.contracts.repositories.business_closure_repositories import (
    BusinessDeletionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.business_closures import BusinessDeletionDocument
from app.schemas.dto.business_closures.business_rows import BusinessTableRows
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.businesses.deletion.deletion_ledger_entries import erasable_tables

logger: logging.Logger = logging.getLogger(__name__)

LEDGER_PAGE: DocumentQueryLimit = DocumentQueryLimit(200)


class ReapplyDeletionLedgerUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Periodic job "reapply_deletion_ledger" (daily, platform pool): a
    database restored from a backup (a point-in-time recovery, the off-site
    backup) may hold rows of businesses deleted since. Every business the
    ledger names (its copy outside the database, and this database's own
    finished entries) loses such rows again, in every table but what the
    law keeps, so a restore never brings a deleted business back. A
    deletion still under way here is left to its own job, which needs the
    business's credentials to switch its providers off first.
    """

    def __init__(
        self,
        deletion_repo: BusinessDeletionRepoContract,
        ledger_mirror: DeletionLedgerMirrorAdapterContract,
        row_eraser: BusinessRowEraserAdapterContract,
    ) -> None:
        self._deletion_repo: BusinessDeletionRepoContract = deletion_repo
        self._ledger_mirror: DeletionLedgerMirrorAdapterContract = ledger_mirror
        self._row_eraser: BusinessRowEraserAdapterContract = row_eraser

    def run(self, input_data: JobTick) -> JobReport:
        deleted: set[BusinessId] = {
            record.business_id for record in self._ledger_mirror.read_all()
        }
        under_way: set[BusinessId] = set()
        for entry in self._entries():
            target = deleted if entry.completed_at is not None else under_way
            target.add(entry.deleted_business_id)

        erased: int = 0
        for business_id in sorted(deleted - under_way, key=str):
            erased += self._erase_again(business_id)

        return JobReport(processed_count=ProcessedItemCount(erased))

    def _entries(self) -> list[BusinessDeletionDocument]:
        entries: list[BusinessDeletionDocument] = []
        after: BusinessDeletionDocument | None = None
        while True:
            page: list[BusinessDeletionDocument] = self._deletion_repo.page_all(
                after, LEDGER_PAGE
            )
            entries += page
            if len(page) < int(LEDGER_PAGE):
                return entries

            after = page[-1]

    def _erase_again(self, business_id: BusinessId) -> int:
        # The queue stays: the deletion's sub-processor erasure jobs wait
        # there (pending, retrying or dead), and erasing them would lose that
        # erasure at Langfuse and ElevenLabs.
        left: list[BusinessTableRows] = erasable_tables(
            self._row_eraser.count_rows(business_id)
        )
        if not left:
            return 0

        erased: list[BusinessTableRows] = self._row_eraser.erase_rows(
            business_id, [count.table for count in left]
        )
        rows: int = sum(int(count.row_count) for count in erased)
        logger.warning(
            "Deletion ledger: deleted business %s had %d rows in %d tables "
            "again (a restore?); deleted them",
            business_id,
            rows,
            len(erased),
        )
        return rows
