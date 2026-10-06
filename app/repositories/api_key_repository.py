from app.contracts.repositories.integration_repositories import (
    ApiKeyChange,
    ApiKeyRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import CREATED_AT_FIELD, ascending, stored_text
from app.schemas.domain.api_keys import ApiKeyDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.integrations.constrained_strings import ApiKeySecretHash
from app.schemas.typings.integrations.prefixed_id import ApiKeyId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

SECRET_HASH_FIELD: DocumentFieldPath = DocumentFieldPath("secret_hash")
# The cabinet caps the keys of a business; a list never reads more.
KEY_LIST_LIMIT: DocumentQueryLimit = DocumentQueryLimit(100)


class ApiKeyRepository(BusinessScopedRepository[ApiKeyDocument], ApiKeyRepoContract):
    """
    API keys, read by business and id, the business's list in creation
    order, and across businesses by the SHA-256 of a whole key (a unique
    index, migration 1181): the one read a request needs before its
    business is known.
    """

    def save(self, api_key: ApiKeyDocument) -> None:
        self._store(str(api_key.id), api_key)

    def get(
        self, business_id: BusinessId, api_key_id: ApiKeyId
    ) -> ApiKeyDocument | None:
        return self._load(business_id, str(api_key_id))

    def update(
        self, business_id: BusinessId, api_key_id: ApiKeyId, change: ApiKeyChange
    ) -> ApiKeyDocument | None:
        return self._modify_in_business(business_id, str(api_key_id), change)

    def list_by_business(self, business_id: BusinessId) -> list[ApiKeyDocument]:
        return self._list_in_business(
            business_id, order=ascending(CREATED_AT_FIELD), limit=KEY_LIST_LIMIT
        )

    def find_by_secret_hash(
        self, secret_hash: ApiKeySecretHash
    ) -> ApiKeyDocument | None:
        return self._collection.find_one_by_field(
            SECRET_HASH_FIELD, stored_text(secret_hash)
        )
