"""
Reading Cal.com answers: a server error, an unreadable body and an
envelope without success are provider errors (never the key in the
reason); numbers and text are read as ids, blanks are nothing; an instant
without a time zone, or not a time at all, is nothing.
"""

import httpx
import pytest

from app.clients.cal_com.cal_com_responses import read_data, read_instant, read_text
from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError

OPERATION = "list bookings"


def answer(status: int, content: bytes) -> httpx.Response:
    return httpx.Response(status, content=content)


@pytest.mark.parametrize(
    "response",
    [
        answer(500, b'{"status": "error"}'),
        answer(200, b"<html>maintenance</html>"),
        answer(200, b'{"status": "error", "data": null}'),
        answer(200, b"[]"),
    ],
)
def test_failed_or_unreadable_answers_fail(
    response: httpx.Response,
) -> None:
    with pytest.raises(BusyTimeSourceError) as raised:
        read_data(response, OPERATION)

    assert raised.value.problem == CalendarSyncProblem.PROVIDER_ERROR
    assert OPERATION in str(raised.value)


def test_a_successful_envelope_gives_its_data() -> None:
    assert read_data(answer(200, b'{"status": "success", "data": [1]}'), OPERATION) == [
        1
    ]


def test_ids_are_read_from_numbers_and_text_and_blanks_are_nothing() -> None:
    fields: dict[str, object] = {
        "id": 1203845,
        "slug": "  table  ",
        "blank": "  ",
        "flag": True,
    }

    assert read_text(fields, "id") == "1203845"
    assert read_text(fields, "slug") == "table"
    assert read_text(fields, "blank") is None
    assert read_text(fields, "flag") is None
    assert read_text(fields, "missing") is None


def test_instants_need_a_time_zone() -> None:
    fields: dict[str, object] = {
        "utc": "2026-10-10T09:00:00.000Z",
        "naive": "2026-10-10T09:00:00",
        "garbage": "next tuesday",
        "number": 1791622800,
    }

    assert read_instant(fields, "utc") == 1791622800  # 2026-10-10 09:00 UTC
    assert read_instant(fields, "naive") is None
    assert read_instant(fields, "garbage") is None
    assert read_instant(fields, "number") is None
