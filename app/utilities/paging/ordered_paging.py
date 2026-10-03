"""
Paging over a list in an order chosen by the reader (name, usage, ...).

Keyset paging needs one comparable sort key; a list sorted by several
mixed keys pages by position instead. The cursor carries the position after
the last item and that item's id: the next page starts right after the item
wherever it moved, or at the position when it is gone.
"""

from collections.abc import Callable, Sequence

from app.schemas.dto.paging import PageRequest
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.utilities.paging.cursor_paging import decode_page_cursor, encode_page_cursor


def take_ordered_page[Item](
    ordered: Sequence[Item],
    page: PageRequest,
    item_id: Callable[[Item], str],
) -> tuple[list[Item], PageCursor | None]:
    """
    One page of an already ordered list and the cursor of the next page
    (None on the last page).

    Raises:
        ValidationFailedError: the cursor is broken.
    """

    start: int = 0
    if page.cursor is not None:
        position, last_id = decode_page_cursor(page.cursor)
        found: int | None = next(
            (index for index, item in enumerate(ordered) if item_id(item) == last_id),
            None,
        )
        start = found + 1 if found is not None else min(max(position, 0), len(ordered))

    end: int = start + int(page.size)
    selected: list[Item] = list(ordered[start:end])
    if end >= len(ordered) or not selected:
        return selected, None

    return selected, encode_page_cursor(end, item_id(selected[-1]))
