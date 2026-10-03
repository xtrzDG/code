"""
Keyset paging over items sorted newest first.

A cursor encodes the sort key (a timestamp) and the id of the last item of
a page, so the next page starts right after it even when new items arrive
in between. Ties on the sort key are broken by the id.
"""

import base64
import binascii
from collections.abc import Callable, Sequence

from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_strings import PageCursor

CURSOR_SEPARATOR: str = ":"
INVALID_CURSOR_MESSAGE: str = "The page cursor is not valid. Load the list again."


def encode_page_cursor(sort_key: int, item_id: str) -> PageCursor:
    """The cursor that points just after the item with this key and id."""

    raw: bytes = f"{sort_key}{CURSOR_SEPARATOR}{item_id}".encode()
    return PageCursor(base64.urlsafe_b64encode(raw).decode().rstrip("="))


def decode_page_cursor(cursor: PageCursor) -> tuple[int, str]:
    """The sort key and item id inside a cursor; ValidationFailedError if broken."""

    text: str = str(cursor)
    padding: str = "=" * (-len(text) % 4)
    try:
        raw: str = base64.urlsafe_b64decode(text + padding).decode()
    except (binascii.Error, UnicodeDecodeError, ValueError) as error:
        raise ValidationFailedError(INVALID_CURSOR_MESSAGE) from error

    raw_key, separator, item_id = raw.partition(CURSOR_SEPARATOR)
    if separator == "" or item_id == "":
        raise ValidationFailedError(INVALID_CURSOR_MESSAGE)

    try:
        return int(raw_key), item_id
    except ValueError as error:
        raise ValidationFailedError(INVALID_CURSOR_MESSAGE) from error


def take_page[Item](
    items: Sequence[Item],
    page: PageRequest,
    sort_key: Callable[[Item], int],
    item_id: Callable[[Item], str],
) -> tuple[list[Item], PageCursor | None]:
    """
    One page of `items` (in any order) sorted by sort key, then id, both
    descending, and the cursor of the next page (None on the last page).
    """

    ordered: list[Item] = sorted(
        items, key=lambda item: (sort_key(item), item_id(item)), reverse=True
    )
    if page.cursor is not None:
        position: tuple[int, str] = decode_page_cursor(page.cursor)
        ordered = [
            item for item in ordered if (sort_key(item), item_id(item)) < position
        ]

    size: int = int(page.size)
    selected: list[Item] = ordered[:size]
    if len(ordered) <= size or not selected:
        return selected, None

    last: Item = selected[-1]
    return selected, encode_page_cursor(sort_key(last), item_id(last))
