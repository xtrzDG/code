"""Playing back a call recording from the conversation card."""

from typing import Any

from fastapi.testclient import TestClient
from typed_time_provider import Microseconds

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

    def play(self, call_id: object, token: str = "staff") -> Any:
        return self.client.get(
            f"/v1/businesses/{self.world.business.id}/calls/{call_id}/recording",
            headers=bearer(token),
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
