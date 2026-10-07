import pytest

from app.gateways.http.paging_query import parse_page_request
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.utilities.paging.cursor_paging import decode_page_cursor, encode_page_cursor


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
