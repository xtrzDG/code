"""The discard_call_recording job: a declined call's audio, gone everywhere."""

import pytest
from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.call_repository import CallRepository
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.conversations import CallDocument
from app.schemas.dto.call_recordings import (
    CallRecordingArchiveJobPayload,
    CallRecordingDiscardJobPayload,
    RecordingAudio,
    RecordingLocation,
)
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_strings import RecordingMediaType
from app.schemas.typings.conversations.strings import (
    ProviderCallId,
    RecordingStoragePath,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.use_cases.voice.recordings.archive_call_recording_use_case import (
    ArchiveCallRecordingUseCase,
)
from app.use_cases.voice.recordings.discard_call_recording_use_case import (
    DiscardCallRecordingUseCase,
)
from tests.channels.recording_storage_fakes import InMemoryRecordingStorage
from tests.compliance.audit_repositories import audit_log_repository

NOW: int = 1_790_855_000_000_000
PLATFORM_COPY = RecordingStoragePath("elevenlabs/conversations/conv_9")
ARCHIVED_COPY = RecordingStoragePath("businesses/b/calls/c.mp3")
AUDIO = RecordingAudio(
    content=b"ID3audio",
    media_type=RecordingMediaType("audio/mpeg"),
)


class DiscardWorld:
    def __init__(self) -> None:
        self.business_id = BusinessId()
        self.calls = CallRepository(InMemoryDocumentCollectionAdapter(CallDocument))
        self.storage = InMemoryRecordingStorage()
        self.audit = audit_log_repository()
        clock: WallClock[Microseconds] = WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: NOW * 1000,
        )
        self.discard = DiscardCallRecordingUseCase(
            self.calls, self.storage, self.audit, clock
        )
        self.archive = ArchiveCallRecordingUseCase(
            self.calls, self.storage, self.audit, clock
        )

    def add_call(
        self, path: RecordingStoragePath | None, *, declined: bool = True
    ) -> CallDocument:
        call = CallDocument(
            business_id=self.business_id,
            started_at=Microseconds(NOW),
            recording_path=path,
            provider_call_id=ProviderCallId("conv_9"),
            recording_declined=declined,
        )
        self.calls.save(call)
        for stored in (PLATFORM_COPY, path):
            if stored is not None:
                self.storage.store(
                    RecordingLocation(business_id=self.business_id, path=stored),
                    AUDIO,
                )
        return call

    def job(self, call: CallDocument) -> QueuedJobInput:
        payload = CallRecordingDiscardJobPayload(call_id=call.id)
        return QueuedJobInput(
            job_id=QueuedJobId(),
            job_name=JobName("discard_call_recording"),
            payload=JobPayloadJson(payload.model_dump_json()),
            business_id=self.business_id,
        )

    def deletions_audited(self) -> int:
        return sum(
            1
            for entry in self.audit.list_by_business(self.business_id)
            if entry.action is AuditAction.DELETE and entry.entity == "call_recording"
        )

    def stored_path(self, call: CallDocument) -> RecordingStoragePath | None:
        stored = self.calls.get(self.business_id, call.id)
        assert stored is not None
        return stored.recording_path


def test_the_platform_copy_and_an_archived_copy_are_deleted_once_audited() -> None:
    world = DiscardWorld()
    call = world.add_call(ARCHIVED_COPY)

    first = world.discard.run(world.job(call))
    again = world.discard.run(world.job(call))

    assert int(first.processed_count) == 1
    assert int(again.processed_count) == 0
    assert world.storage.audio == {}
    assert world.stored_path(call) is None
    assert world.deletions_audited() == 1


def test_a_call_that_kept_its_recording_is_not_touched() -> None:
    world = DiscardWorld()
    call = world.add_call(PLATFORM_COPY, declined=False)

    report = world.discard.run(world.job(call))

    assert int(report.processed_count) == 0
    assert world.storage.deleted == []
    assert world.stored_path(call) == PLATFORM_COPY


def test_an_unreachable_platform_fails_the_job_for_a_retry() -> None:
    world = DiscardWorld()
    call = world.add_call(PLATFORM_COPY)
    world.storage.failure = ExternalServiceError("ElevenLabs is down.")

    with pytest.raises(ExternalServiceError):
        world.discard.run(world.job(call))

    assert world.stored_path(call) == PLATFORM_COPY
    assert world.deletions_audited() == 0
    world.storage.failure = None
    world.discard.run(world.job(call))
    assert world.stored_path(call) is None


def test_a_path_changed_meanwhile_is_left_to_its_writer() -> None:
    world = DiscardWorld()
    call = world.add_call(ARCHIVED_COPY)

    def purge_meanwhile() -> None:
        # A retention purge cleared the call while its audio was deleted.
        def clear(current: CallDocument) -> CallDocument:
            current.recording_path = None
            return current

        world.calls.update(world.business_id, call.id, clear)

    world.storage.on_delete = purge_meanwhile

    report = world.discard.run(world.job(call))

    assert int(report.processed_count) == 0
    assert world.stored_path(call) is None
    assert world.deletions_audited() == 0


def test_a_declined_recording_is_never_archived() -> None:
    world = DiscardWorld()
    call = world.add_call(PLATFORM_COPY)
    payload = CallRecordingArchiveJobPayload(call_id=call.id)

    report = world.archive.run(
        QueuedJobInput(
            job_id=QueuedJobId(),
            job_name=JobName("archive_call_recording"),
            payload=JobPayloadJson(payload.model_dump_json()),
            business_id=world.business_id,
        )
    )

    assert int(report.processed_count) == 0
    assert set(world.storage.audio) == {PLATFORM_COPY}


def test_a_job_without_its_business_is_refused() -> None:
    world = DiscardWorld()
    call = world.add_call(PLATFORM_COPY)
    job = world.job(call).model_copy(update={"business_id": None})

    with pytest.raises(ValidationFailedError):
        world.discard.run(job)
