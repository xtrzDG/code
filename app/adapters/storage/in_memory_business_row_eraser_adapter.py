from collections.abc import Sequence

from app.adapters.storage.in_memory_collection_registry import (
    BusinessDocumentTable,
    InMemoryCollectionRegistry,
)
from app.contracts.business_erasure import BusinessRowEraserAdapterContract
from app.schemas.dto.business_closures.business_rows import BusinessTableRows
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.business_closures.retained_tables import erase_order


class InMemoryBusinessRowEraserAdapter(BusinessRowEraserAdapterContract):
    """
    A business's documents across the process's in-memory collections (the
    registry the storage factory fills): tests and demos without a
    database. Its rows are the documents whose business is the business,
    as Postgres's business column says.
    """

    def __init__(self, registry: InMemoryCollectionRegistry) -> None:
        self._registry: InMemoryCollectionRegistry = registry

    def count_rows(self, business_id: BusinessId) -> list[BusinessTableRows]:
        counts: dict[DocumentCollectionName, int] = {}
        for name, table in self._registry.tables():
            counts[name] = counts.get(name, 0) + int(
                table.count_business_documents(business_id)
            )

        return [
            BusinessTableRows(table=name, row_count=DocumentCount(count))
            for name, count in sorted(counts.items())
            if count > 0
        ]

    def erase_rows(
        self,
        business_id: BusinessId,
        tables: Sequence[DocumentCollectionName] | None = None,
    ) -> list[BusinessTableRows]:
        by_name: dict[DocumentCollectionName, list[BusinessDocumentTable]] = {}
        for name, table in self._registry.tables():
            by_name.setdefault(name, []).append(table)

        chosen: list[DocumentCollectionName] = erase_order(
            list(by_name) if tables is None else list(tables)
        )
        erased: list[BusinessTableRows] = []
        for name in chosen:
            removed: int = sum(
                int(table.remove_business_documents(business_id))
                for table in by_name.get(name, [])
            )
            if removed:
                erased.append(
                    BusinessTableRows(table=name, row_count=DocumentCount(removed))
                )

        return erased
