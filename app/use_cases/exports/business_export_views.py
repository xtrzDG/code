"""
An export as the owner sees it, its archive's place in the export storage,
and the path of a one-time download link.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.privacy import BusinessExportStatus
from app.schemas.domain.business_exports import BusinessExportDocument
from app.schemas.dto.privacy.business_exports import BusinessExportView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.privacy.constrained_integers import ExportDownloadCount
from app.schemas.typings.privacy.constrained_strings import (
    BusinessExportDownloadPath,
    BusinessExportToken,
)
from app.schemas.typings.privacy.prefixed_id import BusinessExportId
from app.schemas.typings.privacy.strings import ExportArchivePath

# An archive opens at most this many times, each through its own link.
MAX_EXPORT_DOWNLOADS: ExportDownloadCount = ExportDownloadCount(3)


def archive_path(
    business_id: BusinessId, export_id: BusinessExportId
) -> ExportArchivePath:
    """Where an export's archive is kept in the export storage."""

    return ExportArchivePath(f"business-exports/{business_id}/{export_id}.zip")


def download_path(
    business_id: BusinessId, export_id: BusinessExportId, token: BusinessExportToken
) -> BusinessExportDownloadPath:
    return BusinessExportDownloadPath(
        f"/v1/business-exports/{business_id}/{export_id}/download?token={token}"
    )


def is_downloadable(export: BusinessExportDocument, now: Microseconds) -> bool:
    """READY, its archive still kept, and downloads left."""

    return (
        export.status is BusinessExportStatus.READY
        and export.archive_path is not None
        and export.expires_at is not None
        and int(export.expires_at) > int(now)
        and int(export.download_count) < int(MAX_EXPORT_DOWNLOADS)
    )


def downloads_left(export: BusinessExportDocument, now: Microseconds) -> int:
    if export.status is not BusinessExportStatus.READY or (
        export.expires_at is not None and int(export.expires_at) <= int(now)
    ):
        return 0

    return max(0, int(MAX_EXPORT_DOWNLOADS) - int(export.download_count))


def build_export_view(
    export: BusinessExportDocument, now: Microseconds
) -> BusinessExportView:
    return BusinessExportView(
        id=export.id,
        status=export.status,
        requested_at=export.created_at,
        finished_at=export.finished_at,
        expires_at=export.expires_at,
        archive_bytes=export.archive_bytes,
        record_count=export.record_count,
        downloads_left=ExportDownloadCount(downloads_left(export, now)),
        last_error=export.last_error,
    )
