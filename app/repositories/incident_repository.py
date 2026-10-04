from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.incidents import IncidentRepoContract
from app.repositories.document_queries import CREATED_AT_FIELD, document_position
from app.schemas.domain.incidents import IncidentDocument
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_pages import DocumentPageQuery
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit


class IncidentRepository(IncidentRepoContract):
    """
    The incident log (a platform collection): pages read by the database,
    newest first, on the (doc_created_at) index of 1093.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[IncidentDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[IncidentDocument] = (
            collection
        )

    def save(self, incident: IncidentDocument) -> None:
        self._collection.upsert(str(incident.id), incident)

    def list_page(self, page: KeysetSlice) -> list[IncidentDocument]:
        return self._collection.page_by(
            DocumentPageQuery(
                sort_fields=(CREATED_AT_FIELD,),
                after=document_position(page.after),
                limit=DocumentQueryLimit(int(page.limit)),
            )
        )
