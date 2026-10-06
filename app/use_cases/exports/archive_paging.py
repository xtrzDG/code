"""Reading a keyset-paged collection whole, for a full export."""

from collections.abc import Callable

from base_pydantic_schemas import BaseDocument

from app.schemas.dto.paging import KeysetSlice, PageRequest
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.utilities.paging.keyset_paging import finish_page, read_slice

PAGE: PageSize = PageSize(200)


def read_all[Document: BaseDocument](
    read_page: Callable[[KeysetSlice], list[Document]],
    sort_key: Callable[[Document], int],
) -> list[Document]:
    """Every document of a keyset-paged collection, a page at a time."""

    documents: list[Document] = []
    cursor: PageCursor | None = None
    while True:
        page = PageRequest(size=PAGE, cursor=cursor)
        items, cursor = finish_page(
            read_page(read_slice(page)),
            page,
            sort_key=sort_key,
            item_id=lambda document: str(document.id),  # type: ignore[attr-defined]
        )
        documents.extend(items)
        if cursor is None:
            return documents
