"""
Deleting the files a visitor left: call recordings, the voice notes and
photos they sent, and the originals of those they sent through the website
chat (the widget's uploads, kept a day apart from the message's own copy).
They go from the storage first, so a storage failure leaves the database
untouched and the erasure can be retried.
"""

from dataclasses import dataclass

from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.contracts.repositories.media_repositories import (
    MessageMediaRepoContract,
    WidgetUploadRepoContract,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.call_recordings import RecordingLocation
from app.schemas.dto.compliance import ContactRecords
from app.schemas.dto.media import MediaLocation
from app.schemas.typings.compliance.constrained_integers import DeletedRecordingCount
from app.schemas.typings.media.prefixed_id import WidgetUploadId
from app.utilities.media.media_paths import widget_upload_id_of_path


@dataclass(frozen=True)
class ContactFileEraser:
    recording_storage: RecordingStorageAdapterContract
    media_storage: MediaStorageAdapterContract
    message_media_repo: MessageMediaRepoContract
    widget_upload_repo: WidgetUploadRepoContract

    def erase(self, records: ContactRecords) -> DeletedRecordingCount:
        """Delete the recordings and the customer's files; recordings deleted."""

        deleted_recordings: int = 0
        for call in records.calls:
            if call.recording_path is not None:
                self.recording_storage.delete(
                    RecordingLocation(
                        business_id=call.business_id, path=call.recording_path
                    )
                )
                deleted_recordings += 1

        for message in records.messages:
            for attachment in message.attachments:
                if attachment.media_id is None or attachment.storage_path is None:
                    continue

                self.media_storage.delete(
                    MediaLocation(
                        business_id=message.business_id, path=attachment.storage_path
                    )
                )
                self.message_media_repo.delete(message.business_id, attachment.media_id)

        for event in records.inbound_events:
            self.erase_widget_uploads(event)

        return DeletedRecordingCount(deleted_recordings)

    def erase_widget_uploads(self, event: InboundEventDocument) -> None:
        """The uploads a website chat message named: their files, then rows."""

        business_id = event.business_id
        if (
            business_id is None
            or event.channel is not ChannelKind.WEB_CHAT
            or event.customer_message is None
        ):
            return

        upload_ids: list[WidgetUploadId] = [
            upload_id
            for attachment in event.customer_message.attachments
            if attachment.provider_media_id is not None
            and (
                upload_id := widget_upload_id_of_path(
                    business_id, str(attachment.provider_media_id)
                )
            )
            is not None
        ]
        for upload in self.widget_upload_repo.get_many(business_id, upload_ids):
            self.media_storage.delete(
                MediaLocation(business_id=business_id, path=upload.storage_path)
            )
            self.widget_upload_repo.delete(business_id, upload.id)
