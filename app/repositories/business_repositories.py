from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories import (
    BusinessRepoContract,
    QuestionnaireRepoContract,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.questionnaires import QuestionnaireDocument
from app.schemas.typings.accounts.prefixed_id import OwnerId
from app.schemas.typings.businesses.prefixed_id import BusinessId


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

    def list_by_owner(self, owner_id: OwnerId) -> list[BusinessDocument]:
        return [
            business
            for business in self._collection.list_all()
            if business.owner_id == owner_id
        ]


class QuestionnaireRepository(QuestionnaireRepoContract):
    """Stores one questionnaire per business, keyed by the business id."""

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[QuestionnaireDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[QuestionnaireDocument] = (
            collection
        )

    def save(self, questionnaire: QuestionnaireDocument) -> None:
        self._collection.upsert(str(questionnaire.business_id), questionnaire)

    def get_by_business(
        self,
        business_id: BusinessId,
    ) -> QuestionnaireDocument | None:
        return self._collection.get(str(business_id))
