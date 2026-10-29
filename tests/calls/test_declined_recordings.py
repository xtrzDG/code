"""A caller who declined the recording: the audio goes, a redacted transcript stays."""

from typing import Any

from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.deliveries import InboundEventStatus
from app.schemas.domain.conversations import CallDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from tests.calls.call_steps import add_staff_chat
from tests.channels.post_call_steps import post_call_payload, process_call, stored_calls
from tests.channels.voice_setup import VoiceSetup, build_voice_setup

PLATFORM_COPY: str = "elevenlabs/conversations/conv_1"
SAID_CONTACTS: str = (
    "Call me on +995 599 12 34 56 or write to nino@example.ge, "
    "the card is 4111 1111 1111 1111, for Saturday at 19:00, 4 people."
)


def declined_payload(*, declined: bool = True) -> dict[str, Any]:
    payload = post_call_payload(tool_names=("decline_recording",) if declined else ())
    payload["data"]["transcript"].append(
        {"role": "user", "message": SAID_CONTACTS, "time_in_call_secs": 80}
    )
    return payload


def only_call(setup: VoiceSetup) -> CallDocument:
    [call] = stored_calls(setup)
    return call


def test_the_audio_is_deleted_and_the_transcript_redacted() -> None:
    setup = build_voice_setup()

    process_call(setup, declined_payload())

    call = only_call(setup)
    assert call.recording_declined is True
    assert call.recording_path is None
    assert setup.testbed.recording_storage.deleted == [PLATFORM_COPY]
    transcript = str(call.transcript)
    assert "[phone]" in transcript and "[email]" in transcript
    assert "[card number]" in transcript
    assert "599 12 34 56" not in transcript and "nino@example.ge" not in transcript
    assert "4111" not in transcript
    # What was agreed stays readable for staff.
    assert "for Saturday at 19:00, 4 people." in transcript
    assert (AuditAction.DELETE.value, "call_recording") in (
        setup.testbed.audit_actions(setup.business.id)
    )


def test_a_call_whose_caller_did_not_decline_keeps_its_recording() -> None:
    setup = build_voice_setup()

    process_call(setup, declined_payload(declined=False))

    call = only_call(setup)
    assert call.recording_declined is False
    assert str(call.recording_path) == PLATFORM_COPY
    assert "nino@example.ge" in str(call.transcript)
    assert setup.testbed.recording_storage.deleted == []


def test_a_later_report_of_the_call_keeps_it_declined() -> None:
    setup = build_voice_setup()
    process_call(setup, declined_payload())
    changed = declined_payload(declined=False)
    changed["data"]["metadata"]["call_duration_secs"] = 96

    process_call(setup, changed)

    call = only_call(setup)
    assert call.recording_declined is True
    assert call.recording_path is None
    assert "nino@example.ge" not in str(call.transcript)
    deletions = [
        action
        for action in setup.testbed.audit_actions(setup.business.id)
        if action == (AuditAction.DELETE.value, "call_recording")
    ]
    assert len(deletions) == 1


def test_staff_are_told_about_the_call_without_its_identifiers() -> None:
    setup = build_voice_setup()
    add_staff_chat(setup, language="en")
    setup.testbed.summary_answers.append('{"ka": "ზარი.", "en": "A call."}')

    process_call(setup, declined_payload())

    [request] = setup.testbed.summary_requests
    asked = str(request.transcript)
    assert "nino@example.ge" not in asked and "4111" not in asked
    assert "[email]" in asked


def answered_reports(setup: VoiceSetup) -> list[InboundEventDocument]:
    return setup.testbed.inbound_event_repo.list_stale(
        InboundEventStatus.ANSWERED,
        Microseconds(2**62),
        DocumentQueryLimit(10),
    )


def test_the_inbox_keeps_no_raw_report_of_a_declined_call() -> None:
    setup = build_voice_setup()

    process_call(setup, declined_payload())

    [report] = answered_reports(setup)
    assert report.payload is None


def test_the_inbox_keeps_the_report_of_a_call_whose_caller_did_not_decline() -> None:
    setup = build_voice_setup()

    process_call(setup, declined_payload(declined=False))

    [report] = answered_reports(setup)
    assert report.payload is not None and "nino@example.ge" in str(report.payload)
