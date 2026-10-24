"""
Meta's webhooks (WhatsApp Cloud API, Messenger, Instagram) through the real
channel adapters. Each fixture starts from Meta's documented examples,
matches the vendor's specification and becomes the expected customer
messages; receipts, echoes, reactions and kinds the platform does not know
are skipped and logged by kind, never raised.
"""

import logging
from typing import Any

import pytest

from app.schemas.dto.channels.channel_webhooks import ChannelInboundMessage
from tests.channels.testbed import ChannelsTestbed
from tests.contracts.contract_files import load_json_fixture
from tests.contracts.meta.meta_cases import (
    OUTSIDE_THE_SPEC,
    PAGE_CASES,
    PAGES_SPEC,
    WHATSAPP_CASES,
    WHATSAPP_SPEC,
    MetaCase,
    adapter_for,
    summarize,
)
from tests.contracts.vendor_schemas import validation_problems
from tests.media.recorded_payloads import as_payload

ALL_CASES: tuple[MetaCase, ...] = WHATSAPP_CASES + PAGE_CASES
MEDIA_FIXTURES: tuple[tuple[str, str], ...] = (
    ("whatsapp_media_webhook.json", WHATSAPP_SPEC),
    ("messenger_media_webhook.json", PAGES_SPEC),
    ("instagram_media_webhook.json", PAGES_SPEC),
)


def spec_of(fixture: str) -> str:
    return WHATSAPP_SPEC if fixture.startswith("whatsapp") else PAGES_SPEC


def parse(case: MetaCase) -> list[ChannelInboundMessage]:
    body: Any = load_json_fixture("meta", case.fixture)
    return adapter_for(ChannelsTestbed(), case.fixture).parse_webhook(as_payload(body))


def fixture_message_ids(body: Any) -> list[str]:
    """The provider ids of the customer messages in a fixture."""

    entry: dict[str, Any] = body["entry"][0]
    if "changes" in entry:
        value: dict[str, Any] = entry["changes"][0]["value"]
        return [message["id"] for message in value.get("messages", [])]

    events: list[dict[str, Any]] = entry["messaging"]
    return [
        (event.get("message") or event.get("postback") or {})["mid"] for event in events
    ]


@pytest.mark.parametrize("case", ALL_CASES, ids=lambda case: case.fixture)
def test_fixture_matches_the_vendor_specification(case: MetaCase) -> None:
    problems = validation_problems(
        load_json_fixture("meta", case.fixture), spec_of(case.fixture), "WebhookPayload"
    )

    if case.fixture in OUTSIDE_THE_SPEC:
        # A field Meta's specification does not list yet: the adapter below
        # must still skip it quietly.
        assert problems != []
    else:
        assert problems == []


@pytest.mark.parametrize(("fixture", "spec"), MEDIA_FIXTURES)
def test_media_fixtures_match_the_vendor_specification(fixture: str, spec: str) -> None:
    assert (
        validation_problems(load_json_fixture("meta", fixture), spec, "WebhookPayload")
        == []
    )


@pytest.mark.parametrize("case", ALL_CASES, ids=lambda case: case.fixture)
def test_adapter_normalizes_the_customer_messages(case: MetaCase) -> None:
    messages = parse(case)

    assert [summarize(message) for message in messages] == list(case.messages)
    if case.messages:
        assert [str(message.provider_message_id) for message in messages] == (
            fixture_message_ids(load_json_fixture("meta", case.fixture))
        )


@pytest.mark.parametrize(
    "case",
    [case for case in ALL_CASES if case.skipped is not None],
    ids=lambda case: case.fixture,
)
def test_skipped_parts_are_logged_by_kind(
    case: MetaCase, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG, logger="app"):
        assert parse(case) == []

    lines = [record.getMessage() for record in caplog.records]
    assert any(f": {case.skipped}." in line for line in lines), lines


def test_unknown_kinds_are_logged_without_their_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    case = next(c for c in ALL_CASES if c.fixture == "messenger_unknown_event.json")
    with caplog.at_level(logging.INFO, logger="app"):
        parse(case)

    [record] = caplog.records
    assert record.levelno == logging.INFO
    assert "message_pin" not in record.getMessage()
    assert "m_AG5Hz2" not in record.getMessage()


@pytest.mark.parametrize(
    ("fixture", "label"),
    [
        ("whatsapp_status_failed_131047.json", "131047 re-engagement window closed"),
        ("whatsapp_status_failed_131026.json", "131026 message undeliverable"),
    ],
)
def test_failed_deliveries_warn_with_their_error_code(
    fixture: str, label: str, caplog: pytest.LogCaptureFixture
) -> None:
    case = next(c for c in WHATSAPP_CASES if c.fixture == fixture)
    with caplog.at_level(logging.WARNING, logger="app"):
        parse(case)

    [warning] = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert label in warning.getMessage()
    # The recipient's number stays out of the logs.
    assert "16505551234" not in warning.getMessage()


def test_receipts_of_own_messages_log_at_debug_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    case = next(
        c for c in WHATSAPP_CASES if c.fixture == "whatsapp_status_delivered.json"
    )
    with caplog.at_level(logging.DEBUG, logger="app"):
        parse(case)

    assert [record.levelno for record in caplog.records] == [logging.DEBUG]
