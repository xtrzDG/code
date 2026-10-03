"""Keyset paging of cabinet lists: which page to return."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.platform.constrained_integers import KeysetReadLimit, PageSize
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.platform.integers import ListSortValue
from app.schemas.typings.platform.strings import ListItemKey

DEFAULT_PAGE_SIZE: PageSize = PageSize(50)


class PageRequest(ImmutableDTO):
    """
    One page of a list sorted newest first.

    `cursor` is the `next_cursor` of the previous page; None asks for the
    first page. Responses carry `items` and `next_cursor` (None on the last
    page).
    """

    size: PageSize = DEFAULT_PAGE_SIZE
    cursor: PageCursor | None = None


class KeysetPosition(ImmutableDTO):
    """
    Where a keyset page starts: just after the item with these sort values
    (in the list's sort order) and this key.
    """

    sort_values: tuple[ListSortValue, ...]
    item_key: ListItemKey


class KeysetSlice(ImmutableDTO):
    """
    What a repository reads for one page of a list: the items after
    `after` (from the start without it), at most `limit` of them.
    """

    after: KeysetPosition | None = None
    limit: KeysetReadLimit
