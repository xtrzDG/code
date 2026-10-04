from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.export_archives import ExportArchiveStorageContract
from app.contracts.privacy import BusinessExportLinkSignerContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.privacy_repositories import (
    BusinessExportRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.privacy import BusinessExportStatus
from app.schemas.domain.business_exports import BusinessExportDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.privacy.business_exports import (
    BusinessExportDownload,
    BusinessExportDownloadQuery,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.privacy.constrained_strings import ExportFileName
from app.use_cases.shared.business_access import require_business
from app.utilities.scheduling.zoned_time import load_time_zone

EXPORT_ENTITY: AuditEntityName = AuditEntityName("business_export")
MICROSECONDS_PER_SECOND: int = 1_000_000


class DownloadBusinessExportUseCase(
    UseCaseContract[BusinessExportDownloadQuery, BusinessExportDownload]
):
    """
    The archive of a READY export through its signed link: the token must be
    the platform's for this export of this business and not expired (the
    link needs no session, so it can be opened on another device). Any
    other token, an expired or purged export, is 404, the same for all. A
    download is audited (EXPORT of "business_export", the IP address).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        export_repo: BusinessExportRepoContract,
        archive_storage: ExportArchiveStorageContract,
        link_signer: BusinessExportLinkSignerContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._export_repo: BusinessExportRepoContract = export_repo
        self._archive_storage: ExportArchiveStorageContract = archive_storage
        self._link_signer: BusinessExportLinkSignerContract = link_signer
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: BusinessExportDownloadQuery) -> BusinessExportDownload:
        now: Microseconds = self._wall_clock.now_unix()
        expiry: Microseconds | None = self._link_signer.expiry_of(
            input_data.business_id, input_data.export_id, input_data.token
        )
        export: BusinessExportDocument | None = (
            None
            if expiry is None or int(expiry) <= int(now)
            else self._export_repo.get(input_data.business_id, input_data.export_id)
        )
        if (
            export is None
            or export.status is not BusinessExportStatus.READY
            or export.archive_path is None
            or export.expires_at is None
            or int(export.expires_at) <= int(now)
        ):
            raise not_found()

        content: bytes | None = self._archive_storage.read(
            export.business_id, export.archive_path
        )
        if content is None:
            raise not_found()

        business: BusinessDocument = require_business(
            self._business_repo, export.business_id
        )
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                action=AuditAction.EXPORT,
                entity=EXPORT_ENTITY,
                entity_id=AuditEntityReference(str(export.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return BusinessExportDownload(
            file_name=archive_file_name(
                export.created_at, load_time_zone(business.timezone)
            ),
            content=content,
        )


def not_found() -> NotFoundError:
    return NotFoundError("This download link is not valid or has expired.")


def archive_file_name(requested_at: Microseconds, zone: ZoneInfo) -> ExportFileName:
    """ "business-export-2026-10-04.zip": the business's day it was asked for."""

    day: str = (
        datetime.fromtimestamp(int(requested_at) / MICROSECONDS_PER_SECOND, tz=UTC)
        .astimezone(zone)
        .date()
        .isoformat()
    )
    return ExportFileName(f"business-export-{day}.zip")
