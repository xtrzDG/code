from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.platform_status import PlatformAnnouncementRepoContract
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    document_position,
    field_equals,
)
from app.schemas.constants.platform_status import AnnouncementStatus
from app.schemas.domain.platform_status import PlatformAnnouncementDocument
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_pages import DocumentPageQuery
from app.schemas.dto.storage_queries import DocumentFieldRange
from app.schemas.typings.platform_status.prefixed_id import AnnouncementId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger

STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
RESOLVED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("resolved_at")


class PlatformAnnouncementRepository(PlatformAnnouncementRepoContract):
    """
    The platform team's announcements (a platform collection, migration
    1111): the active ones by their indexed status, the recently resolved
    ones by the indexed resolution time, the admin's pages by creation
    time.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[PlatformAnnouncementDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            PlatformAnnouncementDocument
        ] = collection

    def get(
        self, announcement_id: AnnouncementId
    ) -> PlatformAnnouncementDocument | None:
        return self._collection.get(str(announcement_id))

    def save(self, announcement: PlatformAnnouncementDocument) -> None:
        self._collection.upsert(str(announcement.id), announcement)

    def list_active(
        self, limit: DocumentQueryLimit
    ) -> list[PlatformAnnouncementDocument]:
        return self._collection.list_by_fields(
            [field_equals(STATUS_FIELD, AnnouncementStatus.ACTIVE)], limit=limit
        )

    def list_resolved_since(
        self, since: Microseconds, limit: DocumentQueryLimit
    ) -> list[PlatformAnnouncementDocument]:
        return self._collection.list_by_range(
            DocumentFieldRange(
                field=RESOLVED_AT_FIELD,
                lower=DocumentFieldInteger(int(since)),
            ),
            is_descending=True,
            limit=limit,
        )

    def list_page(self, page: KeysetSlice) -> list[PlatformAnnouncementDocument]:
        return self._collection.page_by(
            DocumentPageQuery(
                sort_fields=(CREATED_AT_FIELD,),
                after=document_position(page.after),
                limit=DocumentQueryLimit(int(page.limit)),
            )
        )
