"""Sentry gets the release, the log context as tags, no personal data, no secrets."""

import logging
from typing import Any, cast

import pytest
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.types import Event

from app.facilitators.observability.sentry_error_reporting_facilitator import (
    SentryErrorReportingFacilitator,
)
from app.facilitators.observability.sentry_event_scrubbing import (
    scrub_event,
    scrub_transaction,
)
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.observability import WidgetErrorKind, WidgetErrorPhase
from app.schemas.dto.widget_errors import WidgetErrorReport
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_integers import WidgetScriptPosition
from app.schemas.typings.channels.constrained_strings import WidgetErrorName
from app.schemas.typings.platform.constrained_floats import TraceSampleRate
from app.schemas.typings.platform.constrained_strings import (
    JobName,
    ReleaseVersion,
    RequestId,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.observability.log_context import bound_log_context
from tests.platform.test_request_log_context import CapturingHandler

BUSINESS_ID: BusinessId = BusinessId("business_0f8f6bd6-e9b2-4a4c-8b8c-3c1f2a7e9d10")
DSN: PlatformSecret = PlatformSecret("https://key@o1.ingest.de.sentry.io/1")
WIDGET_REPORT: WidgetErrorReport = WidgetErrorReport(
    kind=WidgetErrorKind.SCRIPT_ERROR,
    phase=WidgetErrorPhase.SEND,
    business_id=BUSINESS_ID,
    error_name=WidgetErrorName("TypeError"),
    line=WidgetScriptPosition(1287),
)


class RecordingInit:
    def __init__(self) -> None:
        self.options: dict[str, Any] = {}

    def __call__(self, **options: Any) -> None:
        self.options = options


def enabled_reporter() -> tuple[SentryErrorReportingFacilitator, RecordingInit]:
    init = RecordingInit()
    reporter = SentryErrorReportingFacilitator(
        dsn=DSN,
        environment=DeploymentEnvironment.PRODUCTION,
        release=ReleaseVersion("4718714"),
        traces_sample_rate=TraceSampleRate(0.05),
        sentry_init=init,
    )
    return reporter, init


def test_sentry_is_set_up_with_release_sampling_and_no_personal_data() -> None:
    reporter, init = enabled_reporter()

    assert reporter.is_enabled
    assert init.options["release"] == "4718714"
    assert init.options["environment"] == "production"
    assert init.options["traces_sample_rate"] == 0.05
    assert init.options["send_default_pii"] is False
    assert init.options["max_request_body_size"] == "never"
    assert init.options["auto_enabling_integrations"] is False
    assert init.options["before_send"] is scrub_event
    assert init.options["before_send_transaction"] is scrub_transaction
    assert {type(integration) for integration in init.options["integrations"]} == {
        StarletteIntegration,
        FastApiIntegration,
    }


def test_events_lose_personal_data_and_gain_the_log_context_as_tags() -> None:
    event: Event = {
        "request": {"data": "Hi, my phone is +995..."},
        "user": {"ip_address": "203.0.113.7"},
        "breadcrumbs": {"values": []},
        "tags": {"job_name": "explicit"},
    }
    with bound_log_context(
        request_id=RequestId("req-9"), job_name=JobName("purge_stale_rows")
    ):
        scrubbed = scrub_event(event, {})

    assert scrubbed is not None
    fields: dict[str, Any] = dict(scrubbed)
    assert "request" not in fields and "user" not in fields
    assert "breadcrumbs" not in fields
    assert fields["tags"] == {"job_name": "explicit", "request_id": "req-9"}


def test_traces_keep_no_urls_or_tokens() -> None:
    transaction: dict[str, Any] = {
        "request": {"url": "https://api.example.com/v1/x?session_key=abc"},
        "spans": [
            {
                "description": "POST https://api.telegram.org/bot123:AAH-x/sendMessage?a=1",
                "data": {"url": "https://api.telegram.org/bot123:AAH-x", "kept": 1},
            },
            "not a span",
        ],
    }

    scrubbed = scrub_transaction(cast(Event, transaction), {})

    assert scrubbed is not None
    fields: dict[str, Any] = dict(scrubbed)
    assert "request" not in fields
    span: dict[str, Any] = fields["spans"][0]
    assert (
        span["description"] == "POST https://api.telegram.org/bot<redacted>/sendMessage"
    )
    assert span["data"] == {"kept": 1}


def test_an_error_is_sent_with_the_context_it_was_raised_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reporter, _ = enabled_reporter()
    captured: list[tuple[BaseException, dict[str, str]]] = []

    def capture_exception(error: BaseException, tags: dict[str, str]) -> None:
        captured.append((error, tags))

    monkeypatch.setattr(sentry_sdk, "capture_exception", capture_exception)
    try:
        with bound_log_context(business_id=BUSINESS_ID):
            raise RuntimeError("boom")
    except RuntimeError as error:
        reporter.capture_exception(error)

    assert [tags for _, tags in captured] == [{"business_id": str(BUSINESS_ID)}]


def test_without_a_dsn_errors_are_logged_with_their_context() -> None:
    reporter = SentryErrorReportingFacilitator(
        dsn=None, environment=DeploymentEnvironment.DEVELOPMENT
    )
    handler = CapturingHandler()
    logger = logging.getLogger(
        "app.facilitators.observability.sentry_error_reporting_facilitator"
    )
    logger.addHandler(handler)
    try:
        try:
            with bound_log_context(request_id=RequestId("req-10")):
                raise ValueError("bad")
        except ValueError as error:
            reporter.capture_exception(error)
            reporter.capture_widget_error(WIDGET_REPORT)
    finally:
        logger.removeHandler(handler)

    [record] = handler.records
    assert record.exc_info is not None
    assert record.log_context_fields == {"request_id": "req-10"}  # type: ignore[attr-defined]
    assert not reporter.is_enabled


def test_a_widget_error_becomes_a_grouped_warning(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    reporter, _ = enabled_reporter()
    messages: list[tuple[str, dict[str, Any]]] = []

    def capture_message(message: str, **options: Any) -> None:
        messages.append((message, options))

    monkeypatch.setattr(sentry_sdk, "capture_message", capture_message)

    with caplog.at_level(logging.WARNING, logger="app.widget"):
        reporter.capture_widget_error(WIDGET_REPORT)

    [(message, options)] = messages
    assert message == "Website widget script_error in send"
    assert options["level"] == "warning"
    assert options["tags"]["business_id"] == str(BUSINESS_ID)
    assert options["tags"]["error_name"] == "TypeError"
    assert options["fingerprint"] == [
        "widget",
        "script_error",
        "send",
        "TypeError",
        "1287",
    ]
    assert "Website widget error: kind=script_error" in caplog.text


def test_a_failing_sentry_never_fails_the_caller(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    reporter, _ = enabled_reporter()

    def explode(*arguments: object, **options: object) -> None:
        raise ConnectionError("sentry is down")

    monkeypatch.setattr(sentry_sdk, "capture_exception", explode)
    monkeypatch.setattr(sentry_sdk, "capture_message", explode)

    reporter.capture_exception(RuntimeError("boom"))
    reporter.capture_widget_error(WIDGET_REPORT)

    assert caplog.text.count("Sentry capture failed") == 2
