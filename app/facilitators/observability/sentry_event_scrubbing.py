"""
What reaches Sentry: no request data, users or breadcrumbs (conversations
hold customers' personal data), no secrets in span descriptions, and the
log context as tags.
"""

from collections.abc import Mapping
from typing import cast

from sentry_sdk.types import Event, Hint

from app.utilities.observability.log_context import current_log_context
from app.utilities.observability.log_formatting import redact_secrets

SCRUBBED_EVENT_KEYS: tuple[str, ...] = ("request", "user", "breadcrumbs")
# Span data that may carry URLs with query strings or paths with tokens.
SCRUBBED_SPAN_DATA_KEYS: tuple[str, ...] = (
    "url",
    "http.query",
    "http.fragment",
    "http.request.url",
)


def scrub_event(event: Event, hint: Hint) -> Event | None:
    """Drop request data, user data and breadcrumbs; tag the log context."""

    del hint
    for key in SCRUBBED_EVENT_KEYS:
        event.pop(key, None)  # type: ignore[misc]

    add_context_tags(event, current_log_context().as_fields())
    return event


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
        span["description"] = redact_secrets(description.split("?", 1)[0])

    data: object = span.get("data")
    if isinstance(data, dict):
        span_data = cast(dict[str, object], data)
        for key in SCRUBBED_SPAN_DATA_KEYS:
            span_data.pop(key, None)


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
