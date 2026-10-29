"""Post-call webhook payloads and steps: send a finished call, read stored calls."""

from typing import Any

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.conversations import CallDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from tests.channels.channels_payloads import (
    HttpResponse,
    sign_elevenlabs,
    to_json_bytes,
)
from tests.channels.outbox_reads import outbox_of
from tests.channels.voice_setup import VoiceSetup

# 2026-10-03 15:30 UTC (19:30 in Tbilisi).
BOOKING_STARTS_AT: int = 1_791_041_400


def add_booking(setup: VoiceSetup, party_size: int = 4) -> BookingDocument:
    booking = BookingDocument(
        business_id=setup.business.id,
        resource_id=ResourceId(),
        contact_id=setup.contact.id,
        conversation_id=setup.conversation.id,
        starts_at=BookingStartsAtUnixSeconds(BOOKING_STARTS_AT),
        ends_at=BookingEndsAtUnixSeconds(BOOKING_STARTS_AT + 3600),
        party_size=PartySize(party_size),
        source_channel=ChannelKind.PHONE,
    )
    setup.testbed.booking_repo.save(booking)
    return booking


def post_call_payload(
    conversation_id: str = "conv_1",
    agent_number: str | None = "995322000000",
    external_number: str | None = "+995 599 12 34 56",
    duration: int = 95,
    tool_names: tuple[str, ...] = (),
    caller_spoke: bool = True,
    event_type: str = "post_call_transcription",
    agent_id: str = "agent_1",
    metadata_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    transcript: list[dict[str, Any]] = [
        {
            "role": "agent",
            "message": "გამარჯობა! AI ასისტენტი.",
            "time_in_call_secs": 0,
            "tool_calls": [
                {
                    "request_id": f"r{index}",
                    "tool_name": name,
                    "params_as_json": "{}",
                    "tool_has_been_called": True,
                }
                for index, name in enumerate(tool_names)
            ],
        }
    ]
    if caller_spoke:
        transcript.append(
            {"role": "user", "message": "მაგიდა ოთხისთვის", "time_in_call_secs": 65}
        )
    phone_call: dict[str, Any] = {
        "type": "sip_trunking",
        "direction": "inbound",
        "phone_number_id": "pn_1",
        "call_sid": "sid",
    }
    if agent_number is not None:
        phone_call["agent_number"] = agent_number
    if external_number is not None:
        phone_call["external_number"] = external_number
    metadata: dict[str, Any] = {
        "start_time_unix_secs": 1_790_855_000,
        "call_duration_secs": duration,
        "cost": 296,
        "cost_fiat": 0.1523,
        "main_language": "ka",
        "phone_call": phone_call,
        **(metadata_extra or {}),
    }
    return {
        "type": event_type,
        "event_timestamp": 1_790_855_100,
        "data": {
            "agent_id": agent_id,
            "conversation_id": conversation_id,
            "status": "done",
            "transcript": transcript,
            "metadata": metadata,
            "has_audio": True,
        },
    }


def post_call(
    setup: VoiceSetup,
    payload: dict[str, Any],
    signature: str | None = "valid",
    signed_at: int | None = None,
) -> HttpResponse:
    body: bytes = to_json_bytes(payload)
    headers: dict[str, str] = {}
    if signature == "valid":
        headers["ElevenLabs-Signature"] = sign_elevenlabs(
            body, signed_at or setup.testbed.clock.now_seconds()
        )
    elif signature is not None:
        headers["ElevenLabs-Signature"] = signature
    response: HttpResponse = setup.testbed.build_http_client().post(
        "/v1/voice/webhooks/post-call", content=body, headers=headers
    )
    setup.testbed.run_worker()
    return response


def process_call(setup: VoiceSetup, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Send a signed report and let the worker process it: what the post-call
    flow made of it (status, call id, outcome, confirmation).
    """

    processed_before: int = len(setup.testbed.post_call_outcomes)
    response: HttpResponse = post_call(setup, payload)
    assert response.status_code == 200, response.text
    assert len(setup.testbed.post_call_outcomes) == processed_before + 1
    return setup.testbed.post_call_outcomes[-1].model_dump(mode="json")


def stored_calls(setup: VoiceSetup) -> list[CallDocument]:
    return setup.testbed.call_repo.list_by_business(setup.business.id)


CALL_MESSAGE_KINDS: frozenset[OutboundMessageKind] = frozenset(
    {OutboundMessageKind.CALL_CONFIRMATION, OutboundMessageKind.CALL_LINKS}
)


def queued_call_messages(setup: VoiceSetup) -> list[OutboundMessageDocument]:
    """The confirmations and links queued for callers, oldest first."""

    return [
        message
        for message in outbox_of(setup.testbed, setup.business.id)
        if message.kind in CALL_MESSAGE_KINDS
    ]
