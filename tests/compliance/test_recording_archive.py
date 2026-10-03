"""
A finished call's recording moves from the voice platform into the EU
object storage, sealed with the business's key, and nothing is left behind
or brought back against a purge.
"""

from collections.abc import Generator

import httpx
import pytest
from typed_time_provider import Microseconds

from app.adapters.recordings.cached_recording_storage_adapter import (
    CachedRecordingStorageAdapter,
)
from app.adapters.recordings.encrypted_object_recording_storage_adapter import (
    EncryptedObjectRecordingStorageAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.adapters.voice.elevenlabs_recording_storage_adapter import (
    ElevenLabsRecordingStorageAdapter,
)
from app.clients.elevenlabs.elevenlabs_client import ElevenLabsClient
from app.repositories.call_repository import CallRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import CallDocument
from app.schemas.dto.call_recordings import (
    CallRecordingArchiveJobPayload,
    RecordingAudio,
    RecordingLocation,
)
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.strings import (
    ProviderCallId,
    RecordingStoragePath,
)
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson, PlatformSecret
from app.use_cases.voice.recordings.archive_call_recording_use_case import (
    ArchiveCallRecordingUseCase,
)
from app.use_cases.voice.recordings.recording_archive_paths import (
    ARCHIVE_CALL_RECORDING_JOB,
)
from tests.compliance.moto_object_storage import MotoStorage, moto_storage
from tests.users.accounts_testbed import AdjustableClock

MASTER: PlatformSecret = PlatformSecret("recordings-master-secret-0123456789abcdef")
MP3: bytes = b"ID3\x04" + bytes(range(256)) * 300


class VoicePlatform:
    """ElevenLabs over a MockTransport: the call's audio until it is deleted."""

    def __init__(self, audio: bytes | None = MP3) -> None:
        self.audio: bytes | None = audio
        self.requests: list[str] = []

    def client(self) -> ElevenLabsClient:
        return ElevenLabsClient(
            api_key=PlatformSecret("xi-key"),
            base_url=PublicBaseUrl("https://api.eu.residency.elevenlabs.io"),
            transport=httpx.MockTransport(self._handle),
        )

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(f"{request.method} {request.url.path}")
        if request.method == "DELETE":
            self.audio = None
            return httpx.Response(200, json={})
        if self.audio is None:
            return httpx.Response(404, json={"detail": "not found"})
        return httpx.Response(
            200, content=self.audio, headers={"content-type": "audio/mpeg"}
        )


class ArchiveWorld:
    def __init__(self, storage: MotoStorage, platform: VoicePlatform) -> None:
        self.platform = platform
        self.business_id = BusinessId()
        self.clock = AdjustableClock()
        self.calls = CallRepository(InMemoryDocumentCollectionAdapter(CallDocument))
        self.audit = AuditLogRepository(
            InMemoryDocumentCollectionAdapter(AuditLogEntryDocument)
        )
        self.own = EncryptedObjectRecordingStorageAdapter(storage.client(), MASTER)
        self.recordings = CachedRecordingStorageAdapter(
            ElevenLabsRecordingStorageAdapter(platform.client(), fallback=self.own),
            self.clock.build_wall_clock(),
        )
        self.use_case = ArchiveCallRecordingUseCase(
            call_repo=self.calls,
            recording_storage=self.recordings,
            audit_log_repo=self.audit,
            wall_clock=self.clock.build_wall_clock(),
        )
        self.call = CallDocument(
            business_id=self.business_id,
            started_at=Microseconds(1_790_855_000_000_000),
            provider_call_id=ProviderCallId("conv_42"),
            recording_path=RecordingStoragePath("elevenlabs/conversations/conv_42"),
        )
        self.calls.save(self.call)

    def run(self) -> int:
        return int(
            self.use_case.run(
                QueuedJobInput(
                    job_id=QueuedJobId(),
                    job_name=ARCHIVE_CALL_RECORDING_JOB,
                    payload=JobPayloadJson(
                        CallRecordingArchiveJobPayload(
                            call_id=self.call.id
                        ).model_dump_json()
                    ),
                    business_id=self.business_id,
                )
            ).processed_count
        )

    def stored_call(self) -> CallDocument:
        call = self.calls.get(self.business_id, self.call.id)
        assert call is not None
        return call


@pytest.fixture(scope="module")
def storage() -> Generator[MotoStorage]:
    with moto_storage() as running:
        yield running


def test_the_recording_moves_into_the_eu_bucket_and_leaves_the_platform(
    storage: MotoStorage,
) -> None:
    world = ArchiveWorld(storage, VoicePlatform())

    assert world.run() == 1

    archived_path = f"businesses/{world.business_id}/calls/{world.call.id}.mp3"
    assert str(world.stored_call().recording_path) == archived_path
    assert MP3[100:164] not in storage.raw_object(archived_path)
    played = world.recordings.read(
        RecordingLocation(
            business_id=world.business_id, path=RecordingStoragePath(archived_path)
        )
    )
    assert played is not None and played.content == MP3
    assert world.platform.requests == [
        "GET /v1/convai/conversations/conv_42/audio",
        "DELETE /v1/convai/conversations/conv_42",
    ]
    [entry] = world.audit.list_by_business(world.business_id)
    assert (entry.action, str(entry.entity), entry.actor_id) == (
        AuditAction.UPDATE,
        "call_recording",
        None,
    )


def test_a_repeated_archive_only_makes_sure_the_platform_copy_is_gone(
    storage: MotoStorage,
) -> None:
    world = ArchiveWorld(storage, VoicePlatform())
    world.run()

    assert world.run() == 0
    assert world.platform.requests[-1] == "DELETE /v1/convai/conversations/conv_42"
    assert len(world.audit.list_by_business(world.business_id)) == 1


def test_a_purge_during_the_archive_wins_and_no_copy_is_kept(
    storage: MotoStorage,
) -> None:
    world = ArchiveWorld(storage, VoicePlatform())
    original_store = world.own.store

    def purge_while_storing(location: RecordingLocation, audio: RecordingAudio) -> None:
        original_store(location, audio)
        purged = world.stored_call().model_copy(update={"recording_path": None})
        world.calls.save(purged)

    world.own.store = purge_while_storing  # type: ignore[method-assign]

    assert world.run() == 0
    assert world.stored_call().recording_path is None
    assert not [key for key in storage.object_keys() if str(world.call.id) in key]
    assert world.audit.list_by_business(world.business_id) == []


def test_nothing_to_archive(storage: MotoStorage) -> None:
    without_audio = ArchiveWorld(storage, VoicePlatform(audio=None))
    without_recording = ArchiveWorld(storage, VoicePlatform())
    without_recording.calls.save(
        without_recording.call.model_copy(update={"recording_path": None})
    )

    assert without_audio.run() == 0
    assert without_recording.run() == 0
    assert str(without_audio.stored_call().recording_path).startswith("elevenlabs/")
    assert without_recording.platform.requests == []
