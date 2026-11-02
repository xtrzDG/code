"""
What reaches Sentry: no request data (bodies, headers, cookies, query
strings), users, breadcrumbs, extra data or local variables of a frame
(conversations hold customers' personal data), no e-mail address, phone
number or secret in an error's message, no secrets in span descriptions (a
call to a provider is `METHOD https://host/path-template`, ids and tokens
of the path as `*`), and the log context as tags.
"""

import re
from collections.abc import Mapping
from typing import cast

import httpx
from sentry_sdk.types import Event, Hint

from app.utilities.observability.log_context import current_log_context
from app.utilities.observability.log_formatting import redact_secrets
from app.utilities.observability.tracing.http_client_spans import path_template

SCRUBBED_EVENT_KEYS: tuple[str, ...] = ("request", "user", "breadcrumbs", "extra")
# Contexts an integration may fill from a request or a response.
SCRUBBED_CONTEXT_KEYS: tuple[str, ...] = ("request", "response", "user", "state")
EMAIL_PATTERN: re.Pattern[str] = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Seven digits or more, with the separators a phone number is written with.
PHONE_PATTERN: re.Pattern[str] = re.compile(r"\+?\d(?:[\s().-]?\d){6,}")
REDACTED_EMAIL: str = "<email>"
REDACTED_NUMBER: str = "<number>"
# Span data that may carry URLs with query strings or paths with tokens.
SCRUBBED_SPAN_DATA_KEYS: tuple[str, ...] = (
    "url",
    "http.query",
    "http.fragment",
    "http.request.url",
)
HTTP_CLIENT_OPERATION: str = "http.client"


def scrub_event(event: Event, hint: Hint) -> Event | None:
    """
    Drop request data, user data, breadcrumbs, extra data and the frames'
    local variables; mask e-mails, phones and secrets in the messages; tag
    the log context.
    """

    del hint
    for key in SCRUBBED_EVENT_KEYS:
        event.pop(key, None)  # type: ignore[misc]

    contexts: object = event.get("contexts")
    if isinstance(contexts, dict):
        for key in SCRUBBED_CONTEXT_KEYS:
            cast(dict[str, object], contexts).pop(key, None)

    scrub_exceptions(event)
    scrub_messages(event)
    add_context_tags(event, current_log_context().as_fields())
    return event


def scrub_exceptions(event: Event) -> None:
    """Exceptions and threads keep their frames, without local variables."""

    for key in ("exception", "threads"):
        container: object = event.get(key)
        values: object = (
            cast(dict[str, object], container).get("values")
            if isinstance(container, dict)
            else None
        )
        for value in cast(list[object], values) if isinstance(values, list) else []:
            if not isinstance(value, dict):
                continue

            entry = cast(dict[str, object], value)
            if isinstance(entry.get("value"), str):
                entry["value"] = mask_personal_data(cast(str, entry["value"]))

            scrub_frames(entry.get("stacktrace"))


def scrub_frames(stacktrace: object) -> None:
    frames: object = (
        cast(dict[str, object], stacktrace).get("frames")
        if isinstance(stacktrace, dict)
        else None
    )
    for frame in cast(list[object], frames) if isinstance(frames, list) else []:
        if isinstance(frame, dict):
            cast(dict[str, object], frame).pop("vars", None)


def scrub_messages(event: Event) -> None:
    """The message and the log entry, masked; a log entry's raw params dropped."""

    message: object = event.get("message")
    if isinstance(message, str):
        event["message"] = mask_personal_data(message)

    logentry: object = event.get("logentry")
    if isinstance(logentry, dict):
        entry = cast(dict[str, object], logentry)
        entry.pop("params", None)
        for key in ("message", "formatted"):
            if isinstance(entry.get(key), str):
                entry[key] = mask_personal_data(cast(str, entry[key]))


def mask_personal_data(text: str) -> str:
    """E-mail addresses, phone-like numbers and secrets of a text, masked."""

    masked: str = EMAIL_PATTERN.sub(REDACTED_EMAIL, text)
    return redact_secrets(PHONE_PATTERN.sub(REDACTED_NUMBER, masked))


def scrub_transaction(event: Event, hint: Hint) -> Event | None:
    """A performance trace scrubbed like an error, its spans without URLs."""

    scrubbed: Event | None = scrub_event(event, hint)
    if scrubbed is None:
        return None

    spans: object = scrubbed.get("spans")
    if isinstance(spans, list):
        for span in cast(list[object], spans):
            if isinstance(span, dict):
                scrub_span(cast(dict[str, object], span))

    return scrubbed


def scrub_span(span: dict[str, object]) -> None:
    description: object = span.get("description")
    if isinstance(description, str):
        span["description"] = (
            describe_http_call(description)
            if span.get("op") == HTTP_CLIENT_OPERATION
            else redact_secrets(description.split("?", 1)[0])
        )

    data: object = span.get("data")
    if isinstance(data, dict):
        span_data = cast(dict[str, object], data)
        for key in SCRUBBED_SPAN_DATA_KEYS:
            span_data.pop(key, None)


def describe_http_call(description: str) -> str:
    """`METHOD url` as `METHOD scheme://host/template` (nothing else of the URL)."""

    method, _, raw_url = description.partition(" ")
    try:
        url = httpx.URL(raw_url)
    except httpx.InvalidURL, TypeError, ValueError:
        return method

    if not url.host:
        return method

    return f"{method} {url.scheme}://{url.host}{path_template(url)}"


def add_context_tags(event: Event, fields: Mapping[str, str]) -> None:
    """Add the context fields as tags without replacing tags already set."""

    if not fields:
        return

    tags: object = event.get("tags")
    merged: dict[str, str] = (
        {
            str(name): str(value)
            for name, value in cast(dict[object, object], tags).items()
        }
        if isinstance(tags, dict)
        else {}
    )
    for name, value in fields.items():
        merged.setdefault(name, value)

    event["tags"] = merged
