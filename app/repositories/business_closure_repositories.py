from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureChange,
    BusinessClosureRepoContract,
    BusinessDeletionChange,
    BusinessDeletionRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import field_equals, time_range
from app.schemas.domain.business_closures import (
    BusinessClosureDocument,
    BusinessDeletionDocument,
)
from app.schemas.dto.storage_pages import DocumentPagePosition, DocumentPageQuery
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.business_closures.prefixed_id import BusinessDeletionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.schemas.typings.storage.strings import StoredDocumentKey
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.business_closures.closure_identity import (
    closure_id_for,
    deletion_id_for,
)

DELETE_AFTER_FIELD: DocumentFieldPath = DocumentFieldPath("delete_after")
OWNER_FIELD: DocumentFieldPath = DocumentFieldPath("owners[].user_id")


class BusinessClosureRepository(
    BusinessScopedRepository[BusinessClosureDocument],
    BusinessClosureRepoContract,
):
    """One closure per business under the id derived from it (`closure_id_for`)."""

    def get(self, business_id: BusinessId) -> BusinessClosureDocument | None:
        return self._load(business_id, str(closure_id_for(business_id)))

    def open(self, closure: BusinessClosureDocument) -> bool:
        return bool(self._collection.insert_if_absent(str(closure.id), closure))

    def modify(
        self, business_id: BusinessId, change: BusinessClosureChange
    ) -> BusinessClosureDocument | None:
        return self._modify_in_business(
            business_id, str(closure_id_for(business_id)), change
        )

    def remove(self, business_id: BusinessId) -> None:
        self._remove(business_id, str(closure_id_for(business_id)))

    def page_due(
        self,
        due_at: Microseconds,
        after: BusinessClosureDocument | None,
        limit: DocumentQueryLimit,
    ) -> list[BusinessClosureDocument]:
        return self._collection.page_by(
            DocumentPageQuery(
                where=DocumentFilter(
                    ranges=(
                        time_range(
                            DELETE_AFTER_FIELD,
                            ending_before=Microseconds(int(due_at) + 1),
                        ),
                    )
                ),
                sort_fields=(DELETE_AFTER_FIELD,),
                is_descending=False,
                after=None
                if after is None
                else DocumentPagePosition(
                    values=(DocumentFieldInteger(int(after.delete_after)),),
                    document_key=StoredDocumentKey(str(after.id)),
                ),
                limit=limit,
            )
        )


class BusinessDeletionRepository(BusinessDeletionRepoContract):
    """
    The deletion ledger, platform-wide, one entry per business under the id
    derived from it (`deletion_id_for`), so a deletion begins once.
    """

    def __init__(
        self, collection: DocumentCollectionAdapterContract[BusinessDeletionDocument]
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            BusinessDeletionDocument
        ] = collection

    def begin(self, entry: BusinessDeletionDocument) -> bool:
        return bool(self._collection.insert_if_absent(str(entry.id), entry))

    def get(self, deletion_id: BusinessDeletionId) -> BusinessDeletionDocument | None:
        return self._collection.get(str(deletion_id))

    def find_by_business(
        self, business_id: BusinessId
    ) -> BusinessDeletionDocument | None:
        entry: BusinessDeletionDocument | None = self._collection.get(
            str(deletion_id_for(business_id))
        )
        if entry is None or entry.deleted_business_id != business_id:
            return None

        return entry

    def modify(
        self, deletion_id: BusinessDeletionId, change: BusinessDeletionChange
    ) -> BusinessDeletionDocument | None:
        return self._collection.modify(str(deletion_id), change)

    def list_of_owner(
        self, user_id: UserId, limit: DocumentQueryLimit
    ) -> list[BusinessDeletionDocument]:
        entries: list[BusinessDeletionDocument] = self._collection.list_by_fields(
            [field_equals(OWNER_FIELD, user_id)], limit=limit
        )
        return sorted(entries, key=lambda entry: -int(entry.started_at))
