from typed_time_provider import Microseconds, WallClock

from app.contracts.export_archives import ExportArchiveStorageContract
from app.contracts.repositories.privacy_repositories import (
    BusinessExportRepoContract,
    ExportDownloadLinkRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.privacy import BusinessExportStatus
from app.schemas.domain.business_exports import BusinessExportDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit

BATCH: DocumentQueryLimit = DocumentQueryLimit(200)


class PurgeBusinessExportsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Hourly, across every business: archives whose day ran out are deleted
    from the export storage and their exports become EXPIRED (no archive,
    no expiry left, so the next run does not see them again), and expired
    one-time download links are deleted. A copy of a business's data never
    outlives its day by more than an hour.
    """

    def __init__(
        self,
        export_repo: BusinessExportRepoContract,
        link_repo: ExportDownloadLinkRepoContract,
        archive_storage: ExportArchiveStorageContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._export_repo: BusinessExportRepoContract = export_repo
        self._link_repo: ExportDownloadLinkRepoContract = link_repo
        self._archive_storage: ExportArchiveStorageContract = archive_storage
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        now: Microseconds = self._wall_clock.now_unix()
        purged: int = 0
        for export in self._export_repo.list_expiring_before(now, BATCH):
            if export.archive_path is not None:
                self._archive_storage.delete(export.business_id, export.archive_path)

            self._export_repo.update(
                export.business_id, export.id, lambda current: expired(current, now)
            )
            purged += 1

        self._link_repo.delete_expired_before(now)
        return JobReport(processed_count=ProcessedItemCount(purged))


def expired(
    export: BusinessExportDocument, now: Microseconds
) -> BusinessExportDocument:
    return export.model_copy(
        update={
            "status": BusinessExportStatus.EXPIRED,
            "archive_path": None,
            "expires_at": None,
            "updated_at": now,
        }
    )
