import pytest

from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.utilities.paging.cursor_paging import encode_page_cursor
from app.utilities.paging.ordered_paging import take_ordered_page


def page(size: int, cursor: PageCursor | None = None) -> PageRequest:
    return PageRequest(size=PageSize(size), cursor=cursor)


def test_pages_follow_the_given_order_to_the_end() -> None:
    items = ["d", "a", "c", "b", "e"]

    first, cursor = take_ordered_page(items, page(2), item_id=str)
    second, second_cursor = take_ordered_page(items, page(2, cursor), item_id=str)
    third, last_cursor = take_ordered_page(items, page(2, second_cursor), item_id=str)

    assert (first, second, third) == (["d", "a"], ["c", "b"], ["e"])
    assert last_cursor is None


def test_the_next_page_starts_after_the_last_item_even_when_it_moved() -> None:
    _, cursor = take_ordered_page(["a", "b", "c", "d"], page(2), item_id=str)

    moved, _ = take_ordered_page(
        ["x", "a", "b", "c", "d"], page(2, cursor), item_id=str
    )

    assert moved == ["c", "d"]


def test_a_vanished_item_falls_back_to_the_position() -> None:
    cursor = encode_page_cursor(2, "gone")

    rest, next_cursor = take_ordered_page(["a", "b", "c"], page(5, cursor), item_id=str)

    assert rest == ["c"]
    assert next_cursor is None


def test_an_exact_last_page_has_no_cursor_and_broken_cursors_are_refused() -> None:
    assert take_ordered_page(["a", "b"], page(2), item_id=str) == (["a", "b"], None)
    with pytest.raises(ValidationFailedError):
        take_ordered_page(["a"], page(1, PageCursor("bm9wZQ")), item_id=str)
