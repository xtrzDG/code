"""A deleted business's files: recordings, customers' media, uploads, exports."""

from app.contracts.export_archives import ExportArchiveStorageContract
from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.contracts.repositories.business_document_pages import (
    BusinessDocumentPagesContract,
)
from app.schemas.domain.business_exports import BusinessExportDocument
from app.schemas.domain.conversations import CallDocument
from app.schemas.domain.message_media import MessageMediaDocument
from app.schemas.domain.widget_uploads import WidgetUploadDocument
from app.schemas.dto.call_recordings import RecordingLocation
from app.schemas.dto.media import MediaLocation
from app.schemas.typings.business_closures.constrained_integers import (
    DeletedRowCount,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.shared.document_pages import pages_in_write_order


class BusinessFileEraser:
    """
    Every file the business's rows point at goes from storage before the
    rows do (a storage failure raises, the job retries, nothing is
    orphaned): call recordings, the customers' photos and voice notes, the
    website chat's uploads and the full exports' archives. Deleting a file
    that is gone already is not an error, so a retry repeats safely.
    """

    def __init__(
        self,
        calls: BusinessDocumentPagesContract[CallDocument],
        message_media: BusinessDocumentPagesContract[MessageMediaDocument],
        widget_uploads: BusinessDocumentPagesContract[WidgetUploadDocument],
        business_exports: BusinessDocumentPagesContract[BusinessExportDocument],
        recording_storage: RecordingStorageAdapterContract,
        media_storage: MediaStorageAdapterContract,
        archive_storage: ExportArchiveStorageContract,
    ) -> None:
        self._calls: BusinessDocumentPagesContract[CallDocument] = calls
        self._message_media: BusinessDocumentPagesContract[MessageMediaDocument] = (
            message_media
        )
        self._widget_uploads: BusinessDocumentPagesContract[WidgetUploadDocument] = (
            widget_uploads
        )
        self._business_exports: BusinessDocumentPagesContract[
            BusinessExportDocument
        ] = business_exports
        self._recording_storage: RecordingStorageAdapterContract = recording_storage
        self._media_storage: MediaStorageAdapterContract = media_storage
        self._archive_storage: ExportArchiveStorageContract = archive_storage

    def erase(self, business_id: BusinessId) -> DeletedRowCount:
        """Delete every file of the business; how many there were."""

        deleted: int = 0
        for calls in pages_in_write_order(self._calls, business_id, key_of):
            for call in calls:
                if call.recording_path is not None:
                    self._recording_storage.delete(
                        RecordingLocation(
                            business_id=business_id, path=call.recording_path
                        )
                    )
                    deleted += 1

        for media in pages_in_write_order(self._message_media, business_id, key_of):
            for item in media:
                self._media_storage.delete(
                    MediaLocation(business_id=business_id, path=item.storage_path)
                )
            deleted += len(media)

        for uploads in pages_in_write_order(self._widget_uploads, business_id, key_of):
            for upload in uploads:
                self._media_storage.delete(
                    MediaLocation(business_id=business_id, path=upload.storage_path)
                )
            deleted += len(uploads)

        for exports in pages_in_write_order(
            self._business_exports, business_id, key_of
        ):
            for export in exports:
                if export.archive_path is not None:
                    self._archive_storage.delete(business_id, export.archive_path)
                    deleted += 1

        return DeletedRowCount(deleted)


def key_of(
    document: CallDocument
    | MessageMediaDocument
    | WidgetUploadDocument
    | BusinessExportDocument,
) -> str:
    return str(document.id)
