"""
Sentry never receives personal data: no local variables of a frame, no
default PII or breadcrumbs, and the `before_send` hook drops request
bodies, headers, cookies, query strings, users and extra data and masks
e-mails, phone numbers and secrets in messages.
"""

from typing import Any, cast

from sentry_sdk.types import Event

from app.facilitators.observability.sentry_event_scrubbing import (
    mask_personal_data,
    scrub_event,
)
from tests.platform.test_sentry_reporting import enabled_reporter


def test_sentry_records_no_local_variables_and_no_breadcrumbs() -> None:
    _, init = enabled_reporter()

    assert init.options["include_local_variables"] is False
    assert init.options["max_breadcrumbs"] == 0
    assert init.options["send_default_pii"] is False
    assert init.options["max_request_body_size"] == "never"


def test_request_data_users_extra_and_frame_variables_never_leave() -> None:
    event: dict[str, Any] = {
        "request": {
            "data": {"text": "Book for Giulia, +39 347 123 4567"},
            "headers": {"Authorization": "Bearer secret", "Cookie": "session=1"},
            "cookies": {"session": "1"},
            "query_string": "session_key=abc",
        },
        "user": {"email": "giulia@example.it", "ip_address": "203.0.113.7"},
        "extra": {"customer_text": "my card is 4111 1111 1111 1111"},
        "contexts": {
            "response": {"headers": {"Set-Cookie": "session=1"}},
            "runtime": {"name": "CPython"},
        },
        "exception": {
            "values": [
                {
                    "type": "ValueError",
                    "value": "No contact giulia@example.it at +39 347 123 4567",
                    "stacktrace": {
                        "frames": [
                            {"function": "run", "vars": {"text": "Giulia, allergy"}},
                            {"function": "save"},
                        ]
                    },
                },
                "not an exception",
            ]
        },
        "threads": {
            "values": [{"stacktrace": {"frames": [{"vars": {"token": "abc"}}]}}]
        },
    }

    scrubbed = scrub_event(cast(Event, event), {})

    assert scrubbed is not None
    fields: dict[str, Any] = dict(scrubbed)
    assert not {"request", "user", "extra"} & set(fields)
    assert fields["contexts"] == {"runtime": {"name": "CPython"}}
    [exception, _] = fields["exception"]["values"]
    assert exception["value"] == "No contact <email> at <number>"
    assert exception["stacktrace"]["frames"] == [
        {"function": "run"},
        {"function": "save"},
    ]
    assert fields["threads"]["values"][0]["stacktrace"]["frames"] == [{}]


def test_log_messages_are_masked_and_lose_their_raw_parameters() -> None:
    event: dict[str, Any] = {
        "message": "Reply to +995 555 12 34 56 failed",
        "logentry": {
            "message": "Lead of %s failed",
            "formatted": "Lead of anna.rossi@example.com failed",
            "params": ["anna.rossi@example.com"],
        },
    }

    scrubbed = scrub_event(cast(Event, event), {})

    assert scrubbed is not None
    fields: dict[str, Any] = dict(scrubbed)
    assert fields["message"] == "Reply to <number> failed"
    assert fields["logentry"] == {
        "message": "Lead of %s failed",
        "formatted": "Lead of <email> failed",
    }


def test_ids_and_short_numbers_stay_readable() -> None:
    text = (
        "Business business_0f8f6bd6-e9b2-4a4c-8b8c-3c1f2a7e9d10 has 12 bookings "
        "on port 5432"
    )

    assert mask_personal_data(text) == text
