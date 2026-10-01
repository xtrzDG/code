"""Keyset paging of cabinet lists: which page to return."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.platform.constrained_strings import PageCursor

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
