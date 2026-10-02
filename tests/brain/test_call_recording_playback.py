"""Playing back a call recording from the conversation card."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from typed_time_provider import Microseconds

from app.gateways.http.byte_ranges import (
    ByteRange,
    read_byte_range,
    resolve_byte_range,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import CallDocument
from app.schemas.dto.menu_import import MenuExtraction, MenuExtractionRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_integers import (
    CallDurationSeconds,
)
from app.schemas.typings.conversations.prefixed_id import CallId
from app.schemas.typings.conversations.strings import (
    ProviderCallId,
    RecordingStoragePath,
)
from app.schemas.typings.users.prefixed_id import UserId
from tests.brain.brain_world import BrainWorld, build_world, say, scripted
from tests.brain.cabinet_http import CabinetStorage, bearer, build_cabinet_client

RECORDING_PATH: str = "elevenlabs/conversations/conv_1"
AUDIO: bytes = b"ID3\x04\x00mp3-frames"


class UnusedMenuExtractor:
    def extract(self, request: MenuExtractionRequest) -> MenuExtraction:
        raise AssertionError("Menu extraction is not part of these tests.")


class Playback:
    def __init__(self, world: BrainWorld) -> None:
        self.world = world
        self.storage = CabinetStorage()
        self.client: TestClient = build_cabinet_client(
            world,
            UnusedMenuExtractor(),
            {"owner": world.owner_id, "staff": world.staff_id, "stranger": UserId()},
            self.storage,
        )

    def add_call(
        self,
        recording_path: str | None = RECORDING_PATH,
        business_id: BusinessId | None = None,
    ) -> CallDocument:
        reply = self.world.send("Hi")
        call = CallDocument(
            business_id=business_id or self.world.business.id,
            conversation_id=reply.conversation_id,
            started_at=Microseconds(1_790_855_000_000_000),
            duration_seconds=CallDurationSeconds(95),
            recording_path=(
                None if recording_path is None else RecordingStoragePath(recording_path)
            ),
            provider_call_id=ProviderCallId("conv_1"),
        )
        self.world.call_repo.save(call)
        return call

    def play(
        self,
        call_id: object,
        token: str = "staff",
        byte_range: str | None = None,
        if_range: str | None = None,
    ) -> Any:
        headers: dict[str, str] = bearer(token)
        if byte_range is not None:
            headers["Range"] = byte_range
        if if_range is not None:
            headers["If-Range"] = if_range
        return self.client.get(
            f"/v1/businesses/{self.world.business.id}/calls/{call_id}/recording",
            headers=headers,
        )

    def recording_views(self) -> list[AuditLogEntryDocument]:
        return [
            entry
            for entry in self.world.audit_log_repo.list_by_business(
                self.world.business.id
            )
            if entry.entity == "call_recording"
        ]


def test_owner_and_staff_play_the_recording_and_each_playback_is_audited() -> None:
    playback = Playback(build_world(scripted(say("Hello!"))))
    playback.storage.recording_storage.recordings[RECORDING_PATH] = AUDIO
    call = playback.add_call()

    by_staff = playback.play(call.id, token="staff")
    by_owner = playback.play(call.id, token="owner")

    for response in (by_staff, by_owner):
        assert response.status_code == 200, response.text
        assert response.content == AUDIO
        assert response.headers["content-type"] == "audio/mpeg"
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["accept-ranges"] == "bytes"
    views = playback.recording_views()
    assert [(entry.action, entry.actor_id) for entry in views] == [
        (AuditAction.VIEW, playback.world.staff_id),
        (AuditAction.VIEW, playback.world.owner_id),
    ]
    assert {str(entry.entity_id) for entry in views} == {str(call.id)}
    assert views[0].ip_address == "testclient"


def test_opening_the_card_reads_no_audio() -> None:
    playback = Playback(build_world(scripted(say("Hello!"))))
    playback.storage.recording_storage.recordings[RECORDING_PATH] = AUDIO
    call = playback.add_call()

    card = playback.client.get(
        f"/v1/businesses/{playback.world.business.id}"
        f"/conversations/{call.conversation_id}",
        headers=bearer("owner"),
    )

    assert card.status_code == 200, card.text
    assert card.json()["calls"][0]["recording_path"] == RECORDING_PATH
    assert playback.storage.recording_storage.reads == []
    assert playback.recording_views() == []


def test_purged_missing_and_foreign_recordings_are_not_found() -> None:
    playback = Playback(build_world(scripted(say("a"), say("b"), say("c"))))
    purged = playback.add_call(recording_path=None)
    gone = playback.add_call()  # the platform no longer has its audio
    playback.storage.recording_storage.recordings["elsewhere"] = AUDIO
    foreign = playback.add_call(recording_path="elsewhere", business_id=BusinessId())

    responses = [
        playback.play(purged.id),
        playback.play(gone.id),
        playback.play(foreign.id),
        playback.play(CallId()),
        playback.play("not-a-call-id"),
        playback.play(gone.id, token="stranger"),
    ]

    assert [response.status_code for response in responses] == [404] * 6
    assert responses[0].json()["error"] == "not_found"
    assert "retention" in responses[1].json()["message"]
    assert playback.storage.recording_storage.reads == [RECORDING_PATH]
    assert playback.recording_views() == []


def test_an_unreachable_voice_platform_is_a_bad_gateway() -> None:
    playback = Playback(build_world(scripted(say("Hello!"))))
    playback.storage.recording_storage.failure = "ElevenLabs is down."
    call = playback.add_call()

    response = playback.play(call.id)

    assert response.status_code == 502
    assert response.json()["error"] == "external_service_error"
    assert playback.recording_views() == []


def test_range_requests_get_partial_content_and_a_playback_is_audited_once() -> None:
    # Safari and iOS play only media served in ranges (they probe with
    # bytes=0-1); other browsers ask for later parts to seek.
    playback = Playback(build_world(scripted(say("Hello!"))))
    playback.storage.recording_storage.recordings[RECORDING_PATH] = AUDIO
    call = playback.add_call()
    total = len(AUDIO)

    probe = playback.play(call.id, byte_range="bytes=0-1")
    seek = playback.play(call.id, byte_range="bytes=4-")
    ending = playback.play(call.id, byte_range="bytes=-3")
    past_the_end = playback.play(call.id, byte_range=f"bytes={total + 10}-")
    several = playback.play(call.id, byte_range="bytes=0-1,4-5")
    conditional = playback.play(call.id, byte_range="bytes=4-", if_range='"etag"')

    assert (probe.status_code, probe.content) == (206, AUDIO[:2])
    assert probe.headers["content-range"] == f"bytes 0-1/{total}"
    assert probe.headers["accept-ranges"] == "bytes"
    assert probe.headers["content-type"] == "audio/mpeg"
    assert probe.headers["cache-control"] == "private, no-store"
    assert (seek.status_code, seek.content) == (206, AUDIO[4:])
    assert seek.headers["content-range"] == f"bytes 4-{total - 1}/{total}"
    assert (ending.status_code, ending.content) == (206, AUDIO[-3:])
    assert past_the_end.status_code == 416
    assert past_the_end.headers["content-range"] == f"bytes */{total}"
    # Several ranges, or a range with If-Range, get the whole recording.
    assert (several.status_code, several.content) == (200, AUDIO)
    assert (conditional.status_code, conditional.content) == (200, AUDIO)
    # Only the reads from the beginning start a playback (the probe and the
    # two whole-recording answers); the parts of a playback are not new views.
    assert len(playback.recording_views()) == 3


def test_parts_of_a_playback_still_need_access() -> None:
    playback = Playback(build_world(scripted(say("Hello!"))))
    playback.storage.recording_storage.recordings[RECORDING_PATH] = AUDIO
    call = playback.add_call()

    response = playback.play(call.id, token="stranger", byte_range="bytes=4-")

    assert response.status_code == 404
    assert playback.storage.recording_storage.reads == []


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, None),
        ("bytes=0-1", ByteRange(0, 1)),
        ("bytes=10-", ByteRange(10, None)),
        ("bytes=-500", ByteRange(None, None, 500)),
        (" Bytes=0-1 ", ByteRange(0, 1)),
        ("bytes=5-2", None),
        ("bytes=-", None),
        ("bytes=0-1,4-5", None),
        ("items=0-1", None),
        ("bytes=a-b", None),
    ],
)
def test_one_byte_range_is_read_from_the_header(
    header: str | None,
    expected: ByteRange | None,
) -> None:
    assert read_byte_range(header, None) == expected


def test_byte_ranges_are_clamped_to_the_body() -> None:
    assert resolve_byte_range(ByteRange(0, 1), 10) == (0, 1)
    assert resolve_byte_range(ByteRange(5, 99), 10) == (5, 9)
    assert resolve_byte_range(ByteRange(5, None), 10) == (5, 9)
    assert resolve_byte_range(ByteRange(None, None, 3), 10) == (7, 9)
    assert resolve_byte_range(ByteRange(None, None, 30), 10) == (0, 9)
    assert resolve_byte_range(ByteRange(10, None), 10) is None
    assert resolve_byte_range(ByteRange(None, None, 0), 10) is None
    assert resolve_byte_range(ByteRange(0, None), 0) is None
