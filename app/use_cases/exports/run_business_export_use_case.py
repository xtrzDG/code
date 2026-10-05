import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.export_archives import ExportArchiveStorageContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.privacy_repositories import (
    BusinessExportRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.privacy import BusinessExportStatus
from app.schemas.domain.business_exports import BusinessExportDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.privacy.business_exports import BusinessExportJobPayload
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.privacy.constrained_integers import (
    ExportArchiveByteCount,
    ExportArchiveLifetimeHours,
)
from app.schemas.typings.privacy.strings import ExportArchivePath, ExportErrorText
from app.use_cases.exports.business_archive import BuiltArchive, BusinessArchiveBuilder
from app.use_cases.exports.business_export_views import archive_path
from app.use_cases.shared.business_access import require_business

logger: logging.Logger = logging.getLogger(__name__)

MICROSECONDS_PER_HOUR: int = 3_600 * 1_000_000
# How long a written archive is kept for its downloads: a day.
EXPORT_ARCHIVE_HOURS: ExportArchiveLifetimeHours = ExportArchiveLifetimeHours(24)
FAILED_TEXT: ExportErrorText = ExportErrorText(
    "The archive could not be written. Ask for a new export; if it fails "
    "again, write to support."
)
RUNNABLE: frozenset[BusinessExportStatus] = frozenset(
    {BusinessExportStatus.QUEUED, BusinessExportStatus.RUNNING}
)


class RunBusinessExportUseCase(UseCaseContract[QueuedJobInput, JobReport]):
    """
    The worker writes one full export: the archive of the business's data
    (`BusinessArchiveBuilder`) into the export storage, encrypted with the
    business's key, then the export is READY: owners download it through
    one-time links while the archive is kept (EXPORT_ARCHIVE_HOURS). A
    failure is retried by the queue; the last attempt leaves the export
    FAILED with a reason the owner can read.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        export_repo: BusinessExportRepoContract,
        archive_builder: BusinessArchiveBuilder,
        archive_storage: ExportArchiveStorageContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._export_repo: BusinessExportRepoContract = export_repo
        self._archive_builder: BusinessArchiveBuilder = archive_builder
        self._archive_storage: ExportArchiveStorageContract = archive_storage
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: QueuedJobInput) -> JobReport:
        payload = BusinessExportJobPayload.model_validate_json(str(input_data.payload))
        if input_data.business_id is None:
            return JobReport()

        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        started_at: Microseconds = self._wall_clock.now_unix()
        export: BusinessExportDocument | None = self._export_repo.update(
            business.id,
            payload.export_id,
            lambda current: (
                current.model_copy(
                    update={
                        "status": BusinessExportStatus.RUNNING,
                        "started_at": started_at,
                        "updated_at": started_at,
                    }
                )
                if current.status in RUNNABLE
                else None
            ),
        )
        if export is None:
            return JobReport()

        path: ExportArchivePath = archive_path(business.id, export.id)
        try:
            built: BuiltArchive = self._archive_builder.build(
                business, export.language, started_at
            )
            self._archive_storage.store(business.id, path, built.content)
        except Exception:
            logger.exception("The export %s of %s failed.", export.id, business.id)
            if not input_data.is_final_attempt:
                raise

            self._finish(
                export, BusinessExportStatus.FAILED, {"last_error": FAILED_TEXT}
            )
            return JobReport()

        finished_at: Microseconds = self._wall_clock.now_unix()
        self._finish(
            export,
            BusinessExportStatus.READY,
            {
                "archive_path": path,
                "archive_bytes": ExportArchiveByteCount(len(built.content)),
                "record_count": built.record_count,
                "expires_at": Microseconds(
                    int(finished_at) + int(EXPORT_ARCHIVE_HOURS) * MICROSECONDS_PER_HOUR
                ),
                "last_error": None,
            },
        )
        return JobReport(processed_count=ProcessedItemCount(1))

    def _finish(
        self,
        export: BusinessExportDocument,
        status: BusinessExportStatus,
        fields: dict[str, object],
    ) -> None:
        now: Microseconds = self._wall_clock.now_unix()
        self._export_repo.update(
            export.business_id,
            export.id,
            lambda current: current.model_copy(
                update={
                    **fields,
                    "status": status,
                    "finished_at": now,
                    "updated_at": now,
                }
            ),
        )
