from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.support_access import SupportAccessGrantRepoContract
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import field_equals
from app.schemas.constants.access import SupportAccessStatus
from app.schemas.domain.support_access_grants import SupportAccessGrantDocument
from app.schemas.dto.support_access import SupportAccessEnding
from app.schemas.typings.access.prefixed_id import SupportAccessGrantId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.users.prefixed_id import UserId

STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
ADMIN_USER_ID_FIELD: DocumentFieldPath = DocumentFieldPath("admin_user_id")


class SupportAccessGrantRepository(
    BusinessScopedRepository[SupportAccessGrantDocument],
    SupportAccessGrantRepoContract,
):
    """
    Support access grants (1103): a business's open grants and one admin's
    grants in it on (business_id, doc_status) and (business_id,
    doc_admin_user_id); the open grants of every business on (doc_status)
    for the job that ends expired ones. Ending is a compare-and-swap on
    the status, so a grant ends once.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[SupportAccessGrantDocument],
    ) -> None:
        super().__init__(collection)

    def save(self, grant: SupportAccessGrantDocument) -> None:
        self._store(str(grant.id), grant)

    def get(
        self, business_id: BusinessId, grant_id: SupportAccessGrantId
    ) -> SupportAccessGrantDocument | None:
        return self._load(business_id, str(grant_id))

    def list_open(self, business_id: BusinessId) -> list[SupportAccessGrantDocument]:
        return self._list_in_business(
            business_id, [field_equals(STATUS_FIELD, SupportAccessStatus.OPEN)]
        )

    def list_open_of_admin(
        self, business_id: BusinessId, admin_user_id: UserId
    ) -> list[SupportAccessGrantDocument]:
        return [
            grant
            for grant in self._list_in_business(
                business_id, [field_equals(ADMIN_USER_ID_FIELD, admin_user_id)]
            )
            if grant.status is SupportAccessStatus.OPEN
        ]

    def list_open_everywhere(self) -> list[SupportAccessGrantDocument]:
        return self._collection.list_by_fields(
            [field_equals(STATUS_FIELD, SupportAccessStatus.OPEN)]
        )

    def end(
        self,
        business_id: BusinessId,
        grant_id: SupportAccessGrantId,
        ended: SupportAccessEnding,
    ) -> SupportAccessGrantDocument | None:
        def end_if_open(
            grant: SupportAccessGrantDocument,
        ) -> SupportAccessGrantDocument | None:
            if (
                grant.business_id != business_id
                or grant.status is not SupportAccessStatus.OPEN
            ):
                return None

            grant.status = SupportAccessStatus.ENDED
            grant.ended_at = ended.ended_at
            grant.ended_by = ended.ended_by
            grant.end_reason = ended.reason
            grant.updated_at = ended.ended_at
            return grant

        return self._collection.modify(str(grant_id), end_if_open)
