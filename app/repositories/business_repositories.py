from collections.abc import Callable

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import field_equals
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.constrained_integers import BusinessRevision
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.users.prefixed_id import UserId

MEMBER_USER_ID_FIELD: DocumentFieldPath = DocumentFieldPath("members[].user_id")
CHANNEL_KIND_FIELD: DocumentFieldPath = DocumentFieldPath("kind")
EXTERNAL_ID_FIELD: DocumentFieldPath = DocumentFieldPath("external_id")


class BusinessRepository(BusinessRepoContract):
    """
    Businesses with a revision that grows with every save (optimistic
    concurrency of settings changes, see `save_if_unchanged`). Every write
    reads the stored revision and writes in one step of the collection
    (`modify`), so two writes never end at the same revision and a change
    through `update` is applied to what is stored, not to an older copy.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[BusinessDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[BusinessDocument] = (
            collection
        )

    def save(self, business: BusinessDocument) -> None:
        def overwrite(stored: BusinessDocument) -> BusinessDocument:
            # Never below the stored revision, even when this copy is older;
            # read and written under one lock, so no two saves share one.
            business.revision = BusinessRevision(
                max(int(stored.revision), int(business.revision)) + 1
            )
            return business

        if self._collection.modify(str(business.id), overwrite) is None:
            business.revision = BusinessRevision(int(business.revision) + 1)
            self._collection.upsert(str(business.id), business)

    def update(
        self,
        business_id: BusinessId,
        apply: Callable[[BusinessDocument], None],
    ) -> BusinessDocument:
        unchanged: list[BusinessDocument] = []

        def change(stored: BusinessDocument) -> BusinessDocument | None:
            before: str = stored.model_dump_json()
            apply(stored)
            if stored.model_dump_json() == before:
                unchanged.append(stored)
                return None

            stored.revision = BusinessRevision(int(stored.revision) + 1)
            return stored

        updated: BusinessDocument | None = self._collection.modify(
            str(business_id),
            change,
        )
        if updated is not None:
            return updated

        if unchanged:
            return unchanged[0]

        raise NotFoundError(f"Business {business_id} was not found.")

    def save_if_unchanged(self, business: BusinessDocument) -> bool:
        read_revision: BusinessRevision = business.revision
        business.revision = BusinessRevision(int(read_revision) + 1)
        is_saved: bool = self._collection.replace_if(
            str(business.id),
            business,
            lambda stored: stored.revision == read_revision,
        )
        if not is_saved:
            business.revision = read_revision

        return is_saved

    def get(self, business_id: BusinessId) -> BusinessDocument | None:
        return self._collection.get(str(business_id))

    def list_by_member(self, user_id: UserId) -> list[BusinessDocument]:
        return self._collection.list_by_fields(
            [field_equals(MEMBER_USER_ID_FIELD, user_id)]
        )

    def list_all(self) -> list[BusinessDocument]:
        # Admin client list and the jobs that walk every business.
        return self._collection.list_all()


class ChannelRepository(
    BusinessScopedRepository[ChannelDocument],
    ChannelRepoContract,
):
    def save(self, channel: ChannelDocument) -> None:
        self._store(str(channel.id), channel)

    def get(self, channel_id: ChannelId) -> ChannelDocument | None:
        return self._collection.get(str(channel_id))

    def list_by_business(self, business_id: BusinessId) -> list[ChannelDocument]:
        return self._list_in_business(business_id)

    def modify(
        self,
        business_id: BusinessId,
        channel_id: ChannelId,
        change: Callable[[ChannelDocument], ChannelDocument | None],
    ) -> ChannelDocument | None:
        return self._modify_in_business(business_id, str(channel_id), change)

    def find_by_external_id(
        self,
        kind: ChannelKind,
        external_id: ChannelExternalId,
    ) -> ChannelDocument | None:
        found: list[ChannelDocument] = self._collection.list_by_fields(
            [
                field_equals(CHANNEL_KIND_FIELD, kind),
                field_equals(EXTERNAL_ID_FIELD, external_id),
            ],
            limit=DocumentQueryLimit(1),
        )
        return found[0] if found else None


class BusinessProfileRepository(BusinessProfileRepoContract):
    """Stores one profile per business, keyed by the business id."""

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[BusinessProfileDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[BusinessProfileDocument] = (
            collection
        )

    def save(self, profile: BusinessProfileDocument) -> None:
        self._collection.upsert(str(profile.business_id), profile)

    def get_by_business(
        self,
        business_id: BusinessId,
    ) -> BusinessProfileDocument | None:
        return self._collection.get(str(business_id))

    def insert_if_absent(self, profile: BusinessProfileDocument) -> bool:
        return bool(
            self._collection.insert_if_absent(str(profile.business_id), profile)
        )

    def modify(
        self,
        business_id: BusinessId,
        change: Callable[[BusinessProfileDocument], BusinessProfileDocument | None],
    ) -> BusinessProfileDocument | None:
        return self._collection.modify(str(business_id), change)
