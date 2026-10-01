from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories import (
    HandoffRepoContract,
    UnansweredQuestionRepoContract,
)
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId


class HandoffRepository(HandoffRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[HandoffDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[HandoffDocument] = (
            collection
        )

    def save(self, handoff: HandoffDocument) -> None:
        self._collection.upsert(str(handoff.id), handoff)

    def get(self, handoff_id: HandoffId) -> HandoffDocument | None:
        return self._collection.get(str(handoff_id))

    def list_by_business(self, business_id: BusinessId) -> list[HandoffDocument]:
        handoffs: list[HandoffDocument] = [
            handoff
            for handoff in self._collection.list_all()
            if handoff.business_id == business_id
        ]
        return sorted(handoffs, key=lambda handoff: handoff.created_at, reverse=True)


class UnansweredQuestionRepository(UnansweredQuestionRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[UnansweredQuestionDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            UnansweredQuestionDocument
        ] = collection

    def save(self, question: UnansweredQuestionDocument) -> None:
        self._collection.upsert(str(question.id), question)

    def get(
        self,
        question_id: UnansweredQuestionId,
    ) -> UnansweredQuestionDocument | None:
        return self._collection.get(str(question_id))

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[UnansweredQuestionDocument]:
        questions: list[UnansweredQuestionDocument] = [
            question
            for question in self._collection.list_all()
            if question.business_id == business_id
        ]
        return sorted(
            questions,
            key=lambda question: question.occurrence_count,
            reverse=True,
        )
