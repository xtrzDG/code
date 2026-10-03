from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.conversation_repositories import CallRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.conversations import CallDocument
from app.schemas.dto.call_recordings import CallRecordingArchiveJobPayload
from app.schemas.dto.voice_webhooks import RecordedCall
from app.schemas.typings.conversations.booleans import (
    IsRecordingArchiveEnabled,
    IsRecordingArchiveScheduled,
)
from app.schemas.typings.platform.strings import JobPayloadJson
from app.use_cases.voice.recordings.recording_archive_paths import (
    ARCHIVE_CALL_RECORDING_JOB,
)
from app.utilities.channels.voice_recordings import read_voice_platform_call_id


class ScheduleRecordingArchiveUseCase(
    UseCaseContract[RecordedCall, IsRecordingArchiveScheduled]
):
    """
    After a finished call is stored, queue the archive of its recording from
    the voice platform into the platform's EU object storage (encrypted
    with the business's key; concept: recordings are kept in EU storage
    under the business's retention). Only with RECORDINGS_STORAGE=s3: in
    development the recording stays with the voice platform. A repeated
    webhook queues it again, which is harmless (the archive is idempotent).
    """

    def __init__(
        self,
        call_repo: CallRepoContract,
        job_queue: JobQueueFacilitatorContract,
        is_archive_enabled: IsRecordingArchiveEnabled,
    ) -> None:
        self._call_repo: CallRepoContract = call_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._is_archive_enabled: IsRecordingArchiveEnabled = is_archive_enabled

    def run(self, input_data: RecordedCall) -> IsRecordingArchiveScheduled:
        if (
            not self._is_archive_enabled
            or input_data.business_id is None
            or input_data.call_id is None
        ):
            return False

        call: CallDocument | None = self._call_repo.get(
            input_data.business_id, input_data.call_id
        )
        if (
            call is None
            or call.recording_path is None
            or read_voice_platform_call_id(call.recording_path) is None
        ):
            return False

        self._job_queue.enqueue(
            ARCHIVE_CALL_RECORDING_JOB,
            JobPayloadJson(
                CallRecordingArchiveJobPayload(call_id=call.id).model_dump_json()
            ),
            business_id=call.business_id,
            lane=JobLane.DEFAULT,
        )
        return True
