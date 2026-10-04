from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.media_repositories import MessageMediaRepoContract
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import CREATED_AT_FIELD, time_range
from app.schemas.domain.message_media import MessageMediaDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.media.prefixed_id import MessageMediaId


class MessageMediaRepository(
    BusinessScopedRepository[MessageMediaDocument],
    MessageMediaRepoContract,
):
    """
    Stored customer files by id (derived from the inbox event), and by age
    for the retention purge (`created_at`, indexed with the business,
    migration 1081).
    """

    def save(self, media: MessageMediaDocument) -> None:
        self._store(str(media.id), media)

    def get(
        self, business_id: BusinessId, media_id: MessageMediaId
    ) -> MessageMediaDocument | None:
        return self._load(business_id, str(media_id))

    def get_many(
        self, business_id: BusinessId, media_ids: Sequence[MessageMediaId]
    ) -> list[MessageMediaDocument]:
        if not media_ids:
            return []

        return self._load_many(business_id, [str(media_id) for media_id in media_ids])

    def list_created_before(
        self, business_id: BusinessId, created_before: Microseconds
    ) -> list[MessageMediaDocument]:
        return self._list_in_range(
            business_id, time_range(CREATED_AT_FIELD, ending_before=created_before)
        )

    def delete(self, business_id: BusinessId, media_id: MessageMediaId) -> None:
        self._remove(business_id, str(media_id))
