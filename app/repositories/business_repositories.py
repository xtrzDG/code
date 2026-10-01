from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.users.prefixed_id import UserId


class BusinessRepository(BusinessRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[BusinessDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[BusinessDocument] = (
            collection
        )

    def save(self, business: BusinessDocument) -> None:
        self._collection.upsert(str(business.id), business)

    def get(self, business_id: BusinessId) -> BusinessDocument | None:
        return self._collection.get(str(business_id))

    def list_by_member(self, user_id: UserId) -> list[BusinessDocument]:
        return [
            business
            for business in self._collection.list_all()
            if any(member.user_id == user_id for member in business.members)
        ]

    def list_all(self) -> list[BusinessDocument]:
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
        return self._list(business_id)

    def find_by_external_id(
        self,
        kind: ChannelKind,
        external_id: ChannelExternalId,
    ) -> ChannelDocument | None:
        for channel in self._collection.list_all():
            if channel.kind is kind and channel.external_id == external_id:
                return channel

        return None


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
