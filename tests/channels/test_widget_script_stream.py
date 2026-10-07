"""The widget script's live stream agrees with the API's events route."""

import re

from app.gateways.http.widget_event_routes import WIDGET_EVENTS_PATH
from app.schemas.typings.channels.constrained_strings import WidgetStreamTicket
from tests.channels.widget_script_source import SCRIPT_SOURCE
from tests.channels.widget_tickets import STREAM_TICKET_LENGTH


def read_script_constant(name: str) -> str:
    match = re.search(rf'var {name} = "([^"]*)";', SCRIPT_SOURCE)
    assert match is not None, name
    return match.group(1)


def read_script_number(name: str) -> int:
    match = re.search(rf"var {name} = ([0-9]+);", SCRIPT_SOURCE)
    assert match is not None, name
    return int(match.group(1))


def read_script_pattern(name: str) -> str:
    match = re.search(rf"var {name} = /(.*)/;", SCRIPT_SOURCE)
    assert match is not None, name
    return match.group(1)


def test_the_stream_path_is_the_route_of_the_api() -> None:
    assert read_script_constant("EVENTS_PATH") == WIDGET_EVENTS_PATH


def test_the_script_accepts_exactly_the_tickets_the_api_issues() -> None:
    script_pattern = re.compile(read_script_pattern("STREAM_TICKET_PATTERN"))
    issued = "AQ" + "x" * (STREAM_TICKET_LENGTH - 2)

    assert script_pattern.fullmatch(issued) is not None
    assert WidgetStreamTicket(issued) == issued
    assert script_pattern.fullmatch("short") is None
    assert script_pattern.fullmatch("a" * 40 + "?") is None


def test_the_ticket_rides_in_the_url_and_the_session_key_never_does() -> None:
    # EventSource cannot send headers: the stream is opened with a ticket the
    # widget got in a message body; the session key stays in its header.
    assert "?ticket=" in SCRIPT_SOURCE
    assert "?session_key=" not in SCRIPT_SOURCE
    assert "&session_key=" not in SCRIPT_SOURCE


def test_polling_stays_the_fallback_where_event_source_is_missing() -> None:
    assert "window.EventSource" in SCRIPT_SOURCE
    assert read_script_number("STREAM_SAFETY_POLL_MS") >= 10_000


def test_the_visitor_is_told_before_the_dots_could_hang_for_long() -> None:
    no_answer_after_ms = read_script_number("NO_ANSWER_AFTER_MS")

    assert 60_000 <= no_answer_after_ms <= 120_000
    assert 'noAnswer: "Мы ответим, как только сможем."' in SCRIPT_SOURCE
    assert 'reason: "no_answer"' in SCRIPT_SOURCE
