from typed_time_provider import Microseconds, WallClock

from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.media_repositories import MessageMediaRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.message_media import MessageMediaDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.media import MediaLocation, MessageMediaQuery, StoredMediaFile
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)

MESSAGE_MEDIA_ENTITY: AuditEntityName = AuditEntityName("message_media")
NO_MEDIA_MESSAGE: str = (
    "This file is no longer kept: it was deleted after the retention period "
    "or with the customer's data."
)


class GetMessageMediaUseCase(UseCaseContract[MessageMediaQuery, StoredMediaFile]):
    """
    Owners and staff open a voice note or photo a customer sent, from the
    conversation's transcript. The file stays encrypted in the business's
    media storage and is read only when someone opens it; each opening is
    a view of personal data and is written to the audit log. A file of
    another business, or one the retention purge or an erasure removed, is
    NotFoundError.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        message_media_repo: MessageMediaRepoContract,
        media_storage: MediaStorageAdapterContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._message_media_repo: MessageMediaRepoContract = message_media_repo
        self._media_storage: MediaStorageAdapterContract = media_storage
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: MessageMediaQuery) -> StoredMediaFile:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        media: MessageMediaDocument | None = self._message_media_repo.get(
            business.id, input_data.media_id
        )
        if media is None:
            raise NotFoundError(NO_MEDIA_MESSAGE)

        stored: StoredMediaFile | None = self._media_storage.read(
            MediaLocation(business_id=business.id, path=media.storage_path)
        )
        if stored is None:
            raise NotFoundError(NO_MEDIA_MESSAGE)

        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.VIEW,
                entity=MESSAGE_MEDIA_ENTITY,
                entity_id=AuditEntityReference(str(media.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return stored
