"""How many stored rows of one business a table holds (the deletion's counts)."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName


class BusinessTableRows(ImmutableDTO):
    """The rows of one business in one table (a collection, or a side table)."""

    table: DocumentCollectionName
    row_count: DocumentCount
