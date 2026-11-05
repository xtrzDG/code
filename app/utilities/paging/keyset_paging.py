"""
Keyset pages read by the database (`page_by` of the document store).

The cursor keeps the format of `cursor_paging` (a sort key and the id of
the last item shown), so cursors stay opaque and stable for the cabinet.
A use case turns the cursor into the position the repository starts after
(`read_slice`), the repository reads the page size plus one item, and
`finish_page` returns the page and the next cursor (None on the last page)
without ever loading the whole list.
"""

from collections.abc import Callable, Sequence

from app.schemas.dto.paging import KeysetPosition, KeysetSlice, PageRequest
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.platform.integers import ListSortValue
from app.schemas.typings.platform.strings import ListItemKey
from app.utilities.paging.cursor_paging import decode_page_cursor, encode_page_cursor


def single_value_position(sort_key: int, item_id: str) -> KeysetPosition:
    """The position of a list sorted by one value: the cursor's own key."""

    return KeysetPosition(
        sort_values=(ListSortValue(sort_key),), item_key=ListItemKey(item_id)
    )


def read_slice(
    page: PageRequest,
    position_of: Callable[[int, str], KeysetPosition] = single_value_position,
) -> KeysetSlice:
    """
    What to read for the page: after the cursor's position (decoded by
    `position_of` from its sort key and item id), the page size plus one.

    Raises:
        ValidationFailedError: the cursor is broken.
    """

    after: KeysetPosition | None = None
    if page.cursor is not None:
        sort_key, item_id = decode_page_cursor(page.cursor)
        after = position_of(sort_key, item_id)

    return KeysetSlice(after=after, limit=KeysetReadLimit(int(page.size) + 1))


def finish_page[Item](
    fetched: Sequence[Item],
    page: PageRequest,
    sort_key: Callable[[Item], int],
    item_id: Callable[[Item], str],
) -> tuple[list[Item], PageCursor | None]:
    """
    The page out of the items read for `read_slice(page)`, and the cursor
    of the next page: present when one more item than the page size came.
    """

    size: int = int(page.size)
    items: list[Item] = list(fetched[:size])
    if len(fetched) <= size or not items:
        return items, None

    last: Item = items[-1]
    return items, encode_page_cursor(sort_key(last), item_id(last))
