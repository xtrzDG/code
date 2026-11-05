"""
Every document of one business in bounded keyset pages, in the order they
were first written: a full export streams them, a business's deletion walks
them, and neither ever holds more than one page of a collection.
"""

from collections.abc import Callable, Iterator

from base_pydantic_schemas import BaseDocument

from app.contracts.repositories.business_document_pages import (
    BusinessDocumentPagesContract,
)
from app.schemas.dto.paging import KeysetPosition, KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.platform.strings import ListItemKey

DOCUMENT_PAGE_SIZE: KeysetReadLimit = KeysetReadLimit(1000)


def pages_in_write_order[Document: BaseDocument](
    source: BusinessDocumentPagesContract[Document],
    business_id: BusinessId,
    key_of: Callable[[Document], str],
) -> Iterator[list[Document]]:
    """Every document of the business, a page of 1,000 at a time."""

    after: KeysetPosition | None = None
    while True:
        page: list[Document] = source.page_in_write_order(
            business_id, KeysetSlice(after=after, limit=DOCUMENT_PAGE_SIZE)
        )
        if page:
            yield page

        if len(page) < int(DOCUMENT_PAGE_SIZE):
            return

        after = KeysetPosition(sort_values=(), item_key=ListItemKey(key_of(page[-1])))
