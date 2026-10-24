from collections.abc import Iterable

from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.media_repositories import WidgetUploadRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.widget_uploads import WidgetUploadDocument
from app.schemas.dto.compliance import PurgeExpiredRecordingsCommand
from app.schemas.dto.media import MediaLocation, MessageMediaPurgeResult
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.media.constrained_integers import DeletedMediaCount
from app.use_cases.shared.business_walk import walk_businesses

UPLOAD_LIFETIME_SECONDS: int = 24 * 60 * 60
WIDGET_UPLOAD_ENTITY: AuditEntityName = AuditEntityName("widget_upload")


class PurgeStaleWidgetUploadsUseCase(
    UseCaseContract[PurgeExpiredRecordingsCommand, MessageMediaPurgeResult]
):
    """
    The photos and voice notes website visitors uploaded are kept a day:
    long enough for the message that names them (which copies the file
    into its own, kept for the business's retention), never longer. Each
    upload older than a day is deleted from the media storage with its
    record (an indexed read of the old ones only), attached or not, and
    audited as RETENTION_PURGE without an actor. Running it twice is
    harmless.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        widget_upload_repo: WidgetUploadRepoContract,
        media_storage: MediaStorageAdapterContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._widget_upload_repo: WidgetUploadRepoContract = widget_upload_repo
        self._media_storage: MediaStorageAdapterContract = media_storage
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PurgeExpiredRecordingsCommand) -> MessageMediaPurgeResult:
        businesses: Iterable[BusinessDocument]
        if input_data.business_id is None:
            businesses = walk_businesses(self._business_repo)
        else:
            business: BusinessDocument | None = self._business_repo.get(
                input_data.business_id
            )
            businesses = [] if business is None else [business]

        deleted: int = sum(self._purge_business(business) for business in businesses)
        return MessageMediaPurgeResult(deleted_files=DeletedMediaCount(deleted))

    def _purge_business(self, business: BusinessDocument) -> int:
        now: Microseconds = self._wall_clock.now_unix()
        cutoff: Microseconds = self._wall_clock.now_unix_with_delta(
            Seconds(-UPLOAD_LIFETIME_SECONDS)
        )
        stale: list[WidgetUploadDocument] = (
            self._widget_upload_repo.list_created_before(business.id, cutoff)
        )
        for upload in stale:
            self._media_storage.delete(
                MediaLocation(business_id=business.id, path=upload.storage_path)
            )
            self._widget_upload_repo.delete(business.id, upload.id)
            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    business_id=business.id,
                    action=AuditAction.RETENTION_PURGE,
                    entity=WIDGET_UPLOAD_ENTITY,
                    entity_id=AuditEntityReference(str(upload.id)),
                    created_at=now,
                    updated_at=now,
                )
            )

        return len(stale)
