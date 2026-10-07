"""
Where recordings go: the settings choose local files or the EU bucket, and
a finished call's recording is queued for the archive only with the bucket.
"""

from typing import cast

import pytest
from typed_time_provider import Microseconds

from app.adapters.recordings.encrypted_object_recording_storage_adapter import (
    EncryptedObjectRecordingStorageAdapter,
)
from app.adapters.recordings.local_recording_storage_adapter import (
    LocalRecordingStorageAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.clients.object_storage.s3_object_storage_client import S3ObjectStorageClient
from app.containers.app import AppContainer
from app.contracts.jobs import JobQueueFacilitatorContract, QueuedJobOperator
from app.repositories.call_repository import CallRepository
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.conversations import CallDocument
from app.schemas.dto.call_recordings import CallRecordingArchiveJobPayload
from app.schemas.dto.voice_webhooks import RecordedCall
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import (
    ProviderCallId,
    RecordingStoragePath,
)
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.use_cases.voice.recordings.recording_archive_paths import (
    ARCHIVE_CALL_RECORDING_JOB,
)
from app.use_cases.voice.recordings.schedule_recording_archive_use_case import (
    ScheduleRecordingArchiveUseCase,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.e2e.workshop_container import replace_provider

OBJECT_STORAGE: dict[str, str] = {
    "RECORDINGS_STORAGE": "s3",
    "RECORDINGS_S3_ENDPOINT_URL": "https://s3.eu-central-1.amazonaws.com",
    "RECORDINGS_S3_REGION": "eu-central-1",
    "RECORDINGS_S3_BUCKET": "workshop-recordings-eu",
    "RECORDINGS_S3_ACCESS_KEY_ID": "AKIAEXAMPLE",
    "RECORDINGS_S3_SECRET_ACCESS_KEY": "secret-example",  # gitleaks:allow
    "ENCRYPTION_KEY": "e" * 40,
}


class RecordingJobQueue(JobQueueFacilitatorContract):
    def __init__(self) -> None:
        self.jobs: list[tuple[JobName, JobPayloadJson, BusinessId | None]] = []

    def enqueue(
        self,
        job_name: JobName,
        payload: JobPayloadJson,
        business_id: BusinessId | None,
        run_at: Microseconds | None = None,
        lane: JobLane = JobLane.DEFAULT,
        serial_key: JobSerialKey | None = None,
    ) -> QueuedJobId:
        self.jobs.append((job_name, payload, business_id))
        return QueuedJobId()


def container_for(environment: dict[str, str]) -> AppContainer:
    container = AppContainer()
    replace_provider(container.config.app_settings, assemble_app_settings(environment))
    return container


def test_the_bucket_is_used_with_s3_and_local_files_otherwise() -> None:
    with_bucket = container_for(OBJECT_STORAGE)
    by_default = container_for({})

    assert isinstance(
        with_bucket.adapters.own_recording_storage(),
        EncryptedObjectRecordingStorageAdapter,
    )
    assert isinstance(
        with_bucket.clients.object_storage_client(), S3ObjectStorageClient
    )
    assert isinstance(
        by_default.adapters.own_recording_storage(), LocalRecordingStorageAdapter
    )
    assert by_default.clients.object_storage_client() is None
    operators = cast(
        dict[JobName, QueuedJobOperator],
        with_bucket.gateways.queued_job_operators(),
    )
    assert ARCHIVE_CALL_RECORDING_JOB in operators


@pytest.mark.parametrize(
    ("environment", "message"),
    [
        ({"RECORDINGS_STORAGE": "s3"}, "RECORDINGS_S3_BUCKET"),
        (
            {
                key: value
                for key, value in OBJECT_STORAGE.items()
                if key != "ENCRYPTION_KEY"
            },
            "ENCRYPTION_KEY",
        ),
        ({"RECORDINGS_STORAGE": "ftp"}, "RECORDINGS_STORAGE"),
        (
            {**OBJECT_STORAGE, "RECORDINGS_S3_BUCKET": "Not_A_Bucket"},
            "RECORDINGS_S3_BUCKET",
        ),
    ],
)
def test_an_incomplete_bucket_stops_the_start(
    environment: dict[str, str], message: str
) -> None:
    with pytest.raises(ValidationFailedError, match=message):
        assemble_app_settings(environment)


def build_call(path: str | None) -> tuple[CallRepository, CallDocument]:
    calls = CallRepository(InMemoryDocumentCollectionAdapter(CallDocument))
    call = CallDocument(
        business_id=BusinessId(),
        started_at=Microseconds(1_790_855_000_000_000),
        provider_call_id=ProviderCallId("conv_1"),
        recording_path=None if path is None else RecordingStoragePath(path),
    )
    calls.save(call)
    return calls, call


def recorded(call: CallDocument) -> RecordedCall:
    return RecordedCall(
        status=PostCallEventStatus.RECORDED,
        business_id=call.business_id,
        call_id=call.id,
    )


def test_a_platform_recording_is_queued_for_the_archive() -> None:
    calls, call = build_call("elevenlabs/conversations/conv_1")
    queue = RecordingJobQueue()

    is_scheduled = ScheduleRecordingArchiveUseCase(calls, queue, True).run(
        recorded(call)
    )

    assert is_scheduled is True
    [(job_name, payload, business_id)] = queue.jobs
    assert (job_name, business_id) == (ARCHIVE_CALL_RECORDING_JOB, call.business_id)
    assert CallRecordingArchiveJobPayload.model_validate_json(str(payload)).call_id == (
        call.id
    )


@pytest.mark.parametrize(
    ("path", "is_enabled"),
    [
        ("elevenlabs/conversations/conv_1", False),
        ("businesses/b/calls/c.mp3", True),
        (None, True),
    ],
)
def test_nothing_is_queued_without_the_bucket_or_a_platform_recording(
    path: str | None, is_enabled: bool
) -> None:
    calls, call = build_call(path)
    queue = RecordingJobQueue()
    schedule = ScheduleRecordingArchiveUseCase(calls, queue, is_enabled)

    assert schedule.run(recorded(call)) is False
    assert schedule.run(RecordedCall(status=PostCallEventStatus.RECORDED)) is False
    assert queue.jobs == []
