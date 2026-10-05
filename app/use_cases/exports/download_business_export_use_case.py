from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.export_archives import ExportArchiveStorageContract
from app.contracts.privacy import ExportDownloadNoticeFacilitatorContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.privacy_repositories import (
    BusinessExportRepoContract,
    ExportDownloadLinkRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import BusinessAccessMode
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.business_exports import (
    BusinessExportDocument,
    ExportDownloadLinkDocument,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.privacy.business_exports import (
    BusinessExportDownload,
    BusinessExportDownloadQuery,
    ExportDownloadNotice,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.compliance.constrained_integers import AuditRecordCount
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.privacy.constrained_integers import ExportDownloadCount
from app.schemas.typings.privacy.constrained_strings import (
    ExportDownloadTokenHash,
    ExportFileName,
)
from app.use_cases.exports.business_export_views import (
    MAX_EXPORT_DOWNLOADS,
    is_downloadable,
)
from app.utilities.privacy.export_download_tokens import (
    download_link_id,
    hash_download_token,
    is_same_hash,
)
from app.utilities.scheduling.zoned_time import load_time_zone

EXPORT_ENTITY: AuditEntityName = AuditEntityName("business_export")
MICROSECONDS_PER_SECOND: int = 1_000_000


class DownloadBusinessExportUseCase(
    UseCaseContract[BusinessExportDownloadQuery, BusinessExportDownload]
):
    """
    The archive of a READY export through a one-time link: the token must
    be a link of this export, unused and unexpired, made for the signed-in
    owner who opens it. Any other token, someone else's link, a used or
    expired one, or a deleted archive is 404, the same for all; an export
    downloaded three times is 409.

    The link is used up before the archive is read, and the export's count
    goes up in one atomic step (at most three downloads). Each download is
    audited (EXPORT of "business_export", the address, which download it
    was) and every owner hears of it, with the address and the browser.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        export_repo: BusinessExportRepoContract,
        link_repo: ExportDownloadLinkRepoContract,
        archive_storage: ExportArchiveStorageContract,
        audit_log_repo: AuditLogRepoContract,
        download_notices: ExportDownloadNoticeFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._export_repo: BusinessExportRepoContract = export_repo
        self._link_repo: ExportDownloadLinkRepoContract = link_repo
        self._archive_storage: ExportArchiveStorageContract = archive_storage
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._download_notices: ExportDownloadNoticeFacilitatorContract = (
            download_notices
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: BusinessExportDownloadQuery) -> BusinessExportDownload:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
                access_mode=BusinessAccessMode.WRITE,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        link: ExportDownloadLinkDocument = self._use_link(business, input_data, now)
        export: BusinessExportDocument = self._count_download(business, link, now)
        content: bytes | None = (
            None
            if export.archive_path is None
            else self._archive_storage.read(business.id, export.archive_path)
        )
        if content is None:
            raise not_found()

        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.EXPORT,
                entity=EXPORT_ENTITY,
                entity_id=AuditEntityReference(str(export.id)),
                ip_address=input_data.client_ip_address,
                record_count=AuditRecordCount(int(export.download_count)),
                created_at=now,
                updated_at=now,
            )
        )
        self._download_notices.notice_download(
            business,
            ExportDownloadNotice(
                business_id=business.id,
                export_id=export.id,
                downloaded_by=input_data.user_id,
                client_ip_address=input_data.client_ip_address,
                user_agent=input_data.user_agent,
                download_number=export.download_count,
            ),
        )
        return BusinessExportDownload(
            file_name=archive_file_name(
                export.created_at, load_time_zone(business.timezone)
            ),
            content=content,
        )

    def _use_link(
        self,
        business: BusinessDocument,
        input_data: BusinessExportDownloadQuery,
        now: Microseconds,
    ) -> ExportDownloadLinkDocument:
        """The link of this token, used up now; 404 for anything else."""

        token_hash: ExportDownloadTokenHash = hash_download_token(input_data.token)
        link_id = download_link_id(token_hash)
        link: ExportDownloadLinkDocument | None = self._link_repo.get(
            business.id, link_id
        )
        if (
            link is None
            or not is_same_hash(link.token_hash, token_hash)
            or link.export_id != input_data.export_id
            or link.user_id != input_data.user_id
        ):
            raise not_found()

        used: ExportDownloadLinkDocument | None = self._link_repo.use(
            business.id, link_id, now
        )
        if used is None:
            raise not_found()

        return used

    def _count_download(
        self,
        business: BusinessDocument,
        link: ExportDownloadLinkDocument,
        now: Microseconds,
    ) -> BusinessExportDocument:
        """The export with this download counted (at most three in all)."""

        def count(current: BusinessExportDocument) -> BusinessExportDocument | None:
            if not is_downloadable(current, now):
                return None

            return current.model_copy(
                update={
                    "download_count": ExportDownloadCount(
                        int(current.download_count) + 1
                    ),
                    "updated_at": now,
                }
            )

        counted: BusinessExportDocument | None = self._export_repo.update(
            business.id, link.export_id, count
        )
        if counted is not None:
            return counted

        stored: BusinessExportDocument | None = self._export_repo.get(
            business.id, link.export_id
        )
        if stored is not None and int(stored.download_count) >= int(
            MAX_EXPORT_DOWNLOADS
        ):
            raise ConflictError(
                "This export was downloaded three times already. Ask for a new export."
            )
        raise not_found()


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
