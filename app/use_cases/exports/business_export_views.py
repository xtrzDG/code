"""An export as the owner sees it, with a fresh signed link while READY."""

from typed_time_provider import Microseconds

from app.contracts.privacy import BusinessExportLinkSignerContract
from app.schemas.constants.privacy import BusinessExportStatus
from app.schemas.domain.business_exports import BusinessExportDocument
from app.schemas.dto.privacy.business_exports import BusinessExportView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.privacy.constrained_strings import (
    BusinessExportDownloadPath,
    BusinessExportToken,
)
from app.schemas.typings.privacy.prefixed_id import BusinessExportId
from app.schemas.typings.privacy.strings import ExportArchivePath


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


def build_export_view(
    export: BusinessExportDocument,
    signer: BusinessExportLinkSignerContract,
    now: Microseconds,
) -> BusinessExportView:
    is_downloadable: bool = (
        export.status is BusinessExportStatus.READY
        and export.expires_at is not None
        and int(export.expires_at) > int(now)
    )
    return BusinessExportView(
        id=export.id,
        status=export.status,
        requested_at=export.created_at,
        finished_at=export.finished_at,
        expires_at=export.expires_at,
        archive_bytes=export.archive_bytes,
        record_count=export.record_count,
        download_path=(
            download_path(
                export.business_id,
                export.id,
                signer.sign(export.business_id, export.id, export.expires_at),
            )
            if is_downloadable and export.expires_at is not None
            else None
        ),
        last_error=export.last_error,
    )
