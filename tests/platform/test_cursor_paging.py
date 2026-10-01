import pytest

from app.gateways.http.paging_query import parse_page_request
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.utilities.paging.cursor_paging import (
    decode_page_cursor,
    encode_page_cursor,
    take_page,
)

ITEMS: list[tuple[int, str]] = [
    (300, "c"),
    (100, "a"),
    (200, "b2"),
    (200, "b1"),
    (50, "z"),
]


def page_of(size: int, cursor: PageCursor | None = None) -> PageRequest:
    return PageRequest(size=PageSize(size), cursor=cursor)


def take(page: PageRequest) -> tuple[list[tuple[int, str]], PageCursor | None]:
    return take_page(ITEMS, page, lambda item: item[0], lambda item: item[1])


def test_pages_walk_newest_first_without_gaps_or_repeats() -> None:
    seen: list[tuple[int, str]] = []
    cursor: PageCursor | None = None
    for _ in range(10):
        items, cursor = take(page_of(2, cursor))
        seen.extend(items)
        if cursor is None:
            break

    assert seen == [(300, "c"), (200, "b2"), (200, "b1"), (100, "a"), (50, "z")]


def test_last_page_has_no_cursor() -> None:
    items, cursor = take(page_of(5))

    assert len(items) == 5
    assert cursor is None


def test_items_added_after_the_first_page_do_not_shift_the_next_page() -> None:
    first, cursor = take(page_of(2))
    newer: list[tuple[int, str]] = [(999, "new"), *ITEMS]
    second, _ = take_page(
        newer, page_of(2, cursor), lambda item: item[0], lambda item: item[1]
    )

    assert first == [(300, "c"), (200, "b2")]
    assert second == [(200, "b1"), (100, "a")]


def test_cursor_round_trip_keeps_ids_with_separators() -> None:
    cursor: PageCursor = encode_page_cursor(1790861008853000, "booking:1")

    assert decode_page_cursor(cursor) == (1790861008853000, "booking:1")


@pytest.mark.parametrize("raw", ["bm9wZQ", "OjE", "eDpp"])
def test_cursors_without_a_key_and_id_are_validation_errors(raw: str) -> None:
    with pytest.raises(ValidationFailedError):
        decode_page_cursor(PageCursor(raw))


def test_cursor_with_foreign_characters_is_a_validation_error() -> None:
    with pytest.raises(ValidationFailedError):
        parse_page_request(None, "%%%")


def test_query_defaults_and_limits() -> None:
    assert parse_page_request(None, None) == PageRequest()
    assert parse_page_request("10", "").size == PageSize(10)
    with pytest.raises(ValidationFailedError):
        parse_page_request("0", None)
    with pytest.raises(ValidationFailedError):
        parse_page_request("ten", None)
