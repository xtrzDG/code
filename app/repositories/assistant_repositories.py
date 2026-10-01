from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.typings.assistants.prefixed_id import (
    AssistantVersionId,
    AutotestRunId,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId


class AssistantVersionRepository(AssistantVersionRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[AssistantVersionDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            AssistantVersionDocument
        ] = collection

    def save(self, version: AssistantVersionDocument) -> None:
        self._collection.upsert(str(version.id), version)

    def get(self, version_id: AssistantVersionId) -> AssistantVersionDocument | None:
        return self._collection.get(str(version_id))

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[AssistantVersionDocument]:
        versions: list[AssistantVersionDocument] = [
            version
            for version in self._collection.list_all()
            if version.business_id == business_id
        ]
        return sorted(versions, key=lambda version: version.version_number)


class AutotestRunRepository(AutotestRunRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[AutotestRunDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[AutotestRunDocument] = (
            collection
        )

    def save(self, run: AutotestRunDocument) -> None:
        self._collection.upsert(str(run.id), run)

    def get(self, run_id: AutotestRunId) -> AutotestRunDocument | None:
        return self._collection.get(str(run_id))
