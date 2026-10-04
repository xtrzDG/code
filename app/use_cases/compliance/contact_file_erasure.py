"""
Deleting the files a visitor left: call recordings and the voice notes
and photos they sent. They go from the storage first, so a storage failure
leaves the database untouched and the erasure can be retried.
"""

from dataclasses import dataclass

from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.contracts.repositories.media_repositories import MessageMediaRepoContract
from app.schemas.dto.call_recordings import RecordingLocation
from app.schemas.dto.compliance import ContactRecords
from app.schemas.dto.media import MediaLocation
from app.schemas.typings.compliance.constrained_integers import DeletedRecordingCount


@dataclass(frozen=True)
class ContactFileEraser:
    recording_storage: RecordingStorageAdapterContract
    media_storage: MediaStorageAdapterContract
    message_media_repo: MessageMediaRepoContract

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

        return DeletedRecordingCount(deleted_recordings)
