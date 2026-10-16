"""
ElevenLabs post-call webhooks through the real adapter and the signed
route: every documented event matches its shape (a transcription's data is
the conversation of the SDK's types), a finished call and a call that
could not start are read as the platform expects, and every other event
is skipped, logged by kind and acknowledged with 200.
"""

import logging
from typing import Any

import pytest

from app.adapters.voice.elevenlabs_voice_webhook_adapter import (
    ElevenLabsVoiceWebhookAdapter,
)
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.utilities.channels.channel_endpoints import VOICE_POST_CALL_PATH
from tests.channels.channels_payloads import sign_elevenlabs
from tests.channels.post_call_steps import stored_calls
from tests.channels.voice_setup import VoiceSetup, build_voice_setup
from tests.contracts.contract_files import load_json_fixture, read_fixture_bytes
from tests.contracts.elevenlabs.elevenlabs_cases import (
    AGENTS_SPEC,
    FIXTURE_AGENT_ID,
    WEBHOOKS_SPEC,
)
from tests.contracts.vendor_schemas import assert_inbound

# fixture -> what the webhook answers.
POST_CALL_STATUSES: dict[str, str] = {
    "post_call_transcription.json": "queued",
    "call_initiation_failure.json": "recorded",
    "call_initiation_failure_sip.json": "recorded",
    "post_call_audio.json": "ignored",
    "post_call_unknown_event.json": "ignored",
}
DOCUMENTED_EVENTS: list[str] = sorted(
    name for name in POST_CALL_STATUSES if name != "post_call_unknown_event.json"
)


def adapter() -> ElevenLabsVoiceWebhookAdapter:
    return ElevenLabsVoiceWebhookAdapter(build_voice_setup().testbed.settings)


@pytest.mark.parametrize("fixture", DOCUMENTED_EVENTS)
def test_events_match_the_documented_shapes(fixture: str) -> None:
    assert_inbound(
        load_json_fixture("elevenlabs", fixture), WEBHOOKS_SPEC, "PostCallWebhook"
    )


def test_transcription_data_is_the_conversation_of_the_sdk() -> None:
    event: dict[str, Any] = load_json_fixture(
        "elevenlabs", "post_call_transcription.json"
    )

    assert_inbound(event["data"], AGENTS_SPEC, "Conversation")


def test_finished_call_is_read() -> None:
    report = adapter().parse_post_call(
        read_fixture_bytes("elevenlabs", "post_call_transcription.json")
    )

    assert report is not None
    read: dict[str, Any] = report.model_dump(mode="json")
    assert {key: read[key] for key in read if key != "transcript"} == {
        "provider_call_id": "conv_8401k6contract0001",
        "agent_id": FIXTURE_AGENT_ID,
        "assistant_number": "+995322000000",
        "caller_number": "+995599123456",
        "started_at": 1_790_855_000_000_000,
        "duration_seconds": 95,
        "called_tools": ["create_booking"],
        # cost_fiat, in USD.
        "cost_micro_usd": 152_300,
        "language": "ka",
        "has_recording": True,
        "transfer_offset_seconds": None,
        "transfer_outcome": "not_transferred",
    }
    # The tool turn has no words; the others keep their offsets.
    assert [
        (line["author"], line["offset_seconds"]) for line in read["transcript"]
    ] == [
        ("assistant", 0),
        ("customer", 6),
        ("assistant", 16),
    ]


@pytest.mark.parametrize(
    "fixture", ["call_initiation_failure.json", "call_initiation_failure_sip.json"]
)
def test_call_that_could_not_start_is_read(fixture: str) -> None:
    event: dict[str, Any] = load_json_fixture("elevenlabs", fixture)

    report = adapter().parse_call_start_failure(
        read_fixture_bytes("elevenlabs", fixture)
    )

    assert report is not None
    assert report.model_dump(
        mode="json",
        include={
            "provider_call_id",
            "reason",
            "called_at",
            "assistant_number",
            "caller_number",
        },
    ) == {
        "provider_call_id": event["data"]["conversation_id"],
        "reason": "not_started",
        "called_at": event["event_timestamp"] * 1_000_000,
        "assistant_number": "+995322000000",
        "caller_number": "+995599123456",
    }


@pytest.mark.parametrize(
    ("fixture", "level", "kind"),
    [
        ("post_call_audio.json", logging.DEBUG, "post_call_audio"),
        ("post_call_unknown_event.json", logging.INFO, "other"),
    ],
)
def test_other_events_are_skipped_and_logged_by_kind(
    fixture: str, level: int, kind: str, caplog: pytest.LogCaptureFixture
) -> None:
    body: bytes = read_fixture_bytes("elevenlabs", fixture)
    webhook_adapter = adapter()

    with caplog.at_level(logging.DEBUG, logger="app"):
        finished = webhook_adapter.parse_post_call(body)
        failed_start = webhook_adapter.parse_call_start_failure(body)

    assert (finished, failed_start) == (None, None)
    [record] = caplog.records
    assert record.levelno == level
    assert record.getMessage().endswith(f": {kind}=1.")
    # The event's content stays out of the log.
    assert "conv_" not in record.getMessage()


def answering_setup() -> VoiceSetup:
    """A business whose published version is the fixtures' agent."""

    setup = build_voice_setup()
    version = setup.testbed.assistant_version_repo.get(
        setup.business.id, setup.conversation.assistant_version_id
    )
    assert version is not None
    version.voice_agent_id = VoiceAgentId(FIXTURE_AGENT_ID)
    setup.testbed.assistant_version_repo.save(version)
    return setup


@pytest.mark.parametrize("fixture", sorted(POST_CALL_STATUSES))
def test_signed_events_are_acknowledged(fixture: str) -> None:
    setup = answering_setup()
    body: bytes = read_fixture_bytes("elevenlabs", fixture)

    response = setup.testbed.build_http_client().post(
        VOICE_POST_CALL_PATH,
        content=body,
        headers={
            # The real signature: HMAC-SHA256 of "<t>.<raw body>".
            "ElevenLabs-Signature": sign_elevenlabs(
                body, setup.testbed.clock.now_seconds()
            ),
        },
    )
    setup.testbed.run_worker()

    assert response.status_code == 200, response.text
    assert response.json()["status"] == POST_CALL_STATUSES[fixture]
    if fixture == "post_call_transcription.json":
        [call] = stored_calls(setup)
        assert call.duration_seconds == 95
