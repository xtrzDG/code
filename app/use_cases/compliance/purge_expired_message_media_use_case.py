from collections.abc import Iterable

from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.repositories.media_repositories import MessageMediaRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.message_media import MessageMediaDocument
from app.schemas.dto.compliance import PurgeExpiredRecordingsCommand
from app.schemas.dto.media import MediaLocation, MessageMediaPurgeResult
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.media.constrained_integers import DeletedMediaCount
from app.use_cases.shared.business_walk import walk_businesses

SECONDS_PER_DAY: int = 24 * 60 * 60
MESSAGE_MEDIA_ENTITY: AuditEntityName = AuditEntityName("message_media")


class PurgeExpiredMessageMediaUseCase(
    UseCaseContract[PurgeExpiredRecordingsCommand, MessageMediaPurgeResult]
):
    """
    Retention of the files customers send, like call recordings: voice
    notes and photos stored more than the business's
    `recording_retention_days` ago are deleted from the media storage (an
    indexed read of the old ones only). The message keeps its transcript
    and says the file was removed; each file is audited as RETENTION_PURGE
    without an actor. Running it twice is harmless.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        message_media_repo: MessageMediaRepoContract,
        message_repo: MessageRepoContract,
        media_storage: MediaStorageAdapterContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._message_media_repo: MessageMediaRepoContract = message_media_repo
        self._message_repo: MessageRepoContract = message_repo
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
            Seconds(-int(business.recording_retention_days) * SECONDS_PER_DAY)
        )
        expired: list[MessageMediaDocument] = (
            self._message_media_repo.list_created_before(business.id, cutoff)
        )
        for media in expired:
            self._media_storage.delete(
                MediaLocation(business_id=business.id, path=media.storage_path)
            )
            self._mark_message(media, now)
            self._message_media_repo.delete(business.id, media.id)
            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    business_id=business.id,
                    action=AuditAction.RETENTION_PURGE,
                    entity=MESSAGE_MEDIA_ENTITY,
                    entity_id=AuditEntityReference(str(media.id)),
                    created_at=now,
                    updated_at=now,
                )
            )

        return len(expired)

    def _mark_message(self, media: MessageMediaDocument, now: Microseconds) -> None:
        """The message says its file is gone (its transcript stays)."""

        message: MessageDocument | None = self._message_repo.get(
            media.business_id, media.message_id
        )
        if message is None:
            return

        message.attachments = [
            attachment.model_copy(update={"media_deleted_at": now})
            if attachment.media_id == media.id
            else attachment
            for attachment in message.attachments
        ]
        message.updated_at = now
        self._message_repo.save(message)
