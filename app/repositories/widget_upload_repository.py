from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.media_repositories import WidgetUploadRepoContract
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import CREATED_AT_FIELD, time_range
from app.schemas.domain.widget_uploads import WidgetUploadDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import WidgetVisitorId
from app.schemas.typings.media.prefixed_id import WidgetUploadId


class WidgetUploadRepository(
    BusinessScopedRepository[WidgetUploadDocument],
    WidgetUploadRepoContract,
):
    """
    Files website chat visitors uploaded, by id (the message names them),
    claimed once by their own visitor, and by age for the daily purge
    (`created_at`, indexed with the business, migration 1191).
    """

    def save(self, upload: WidgetUploadDocument) -> None:
        self._store(str(upload.id), upload)

    def get_many(
        self, business_id: BusinessId, upload_ids: Sequence[WidgetUploadId]
    ) -> list[WidgetUploadDocument]:
        if not upload_ids:
            return []

        return self._load_many(
            business_id, [str(upload_id) for upload_id in upload_ids]
        )

    def claim(
        self,
        business_id: BusinessId,
        upload_id: WidgetUploadId,
        visitor_id: WidgetVisitorId,
        at: Microseconds,
    ) -> WidgetUploadDocument | None:
        def attach(stored: WidgetUploadDocument) -> WidgetUploadDocument | None:
            if stored.visitor_id != visitor_id or stored.attached_at is not None:
                return None

            return stored.model_copy(update={"attached_at": at, "updated_at": at})

        return self._modify_in_business(business_id, str(upload_id), attach)

    def release(self, business_id: BusinessId, upload_id: WidgetUploadId) -> None:
        def detach(stored: WidgetUploadDocument) -> WidgetUploadDocument:
            return stored.model_copy(update={"attached_at": None})

        self._modify_in_business(business_id, str(upload_id), detach)

    def list_created_before(
        self, business_id: BusinessId, created_before: Microseconds
    ) -> list[WidgetUploadDocument]:
        return self._list_in_range(
            business_id, time_range(CREATED_AT_FIELD, ending_before=created_before)
        )

    def delete(self, business_id: BusinessId, upload_id: WidgetUploadId) -> None:
        self._remove(business_id, str(upload_id))
