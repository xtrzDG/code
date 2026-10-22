from typed_time_provider import Microseconds, WallClock

from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import CallRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import CallDocument
from app.schemas.dto.call_recordings import (
    CallRecordingDiscardJobPayload,
    RecordingLocation,
)
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.voice.recordings.archive_call_recording_use_case import (
    CALL_RECORDING_ENTITY,
)
from app.utilities.channels.voice_recordings import (
    build_voice_platform_recording_path,
    read_voice_platform_call_id,
)


class DiscardCallRecordingUseCase(UseCaseContract[QueuedJobInput, JobReport]):
    """
    Queued job "discard_call_recording": the caller declined the recording,
    so its audio goes. The voice platform's conversation (its audio and its
    own transcript) is deleted, and so is an archived copy the call points
    to; then the call stops pointing to a recording, in one step and only
    while it still points to the deleted one. The deletion is written to
    the audit log once. The call keeps its redacted transcript.

    Idempotent: a retry deletes what is left (deleting a missing recording
    is not an error) and changes nothing else. A storage that cannot be
    reached raises, so the job queue tries again with backoff (and the dead
    letters keep a deletion that keeps failing, for the team).
    """

    def __init__(
        self,
        call_repo: CallRepoContract,
        recording_storage: RecordingStorageAdapterContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._call_repo: CallRepoContract = call_repo
        self._recording_storage: RecordingStorageAdapterContract = recording_storage
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: QueuedJobInput) -> JobReport:
        business_id: BusinessId | None = input_data.business_id
        if business_id is None:
            raise ValidationFailedError("A recording discard job names no business.")

        payload = CallRecordingDiscardJobPayload.model_validate_json(
            str(input_data.payload)
        )
        call: CallDocument | None = self._call_repo.get(business_id, payload.call_id)
        if call is None or not call.recording_declined:
            return discarded(0)

        self._recording_storage.delete(
            RecordingLocation(
                business_id=business_id,
                path=build_voice_platform_recording_path(call.provider_call_id),
            )
        )
        stored_path: RecordingStoragePath | None = call.recording_path
        if stored_path is None:
            return discarded(0)

        if read_voice_platform_call_id(stored_path) is None:
            self._recording_storage.delete(
                RecordingLocation(business_id=business_id, path=stored_path)
            )

        now: Microseconds = self._wall_clock.now_unix()

        def forget(current: CallDocument) -> CallDocument | None:
            if current.recording_path != stored_path:
                return None

            current.recording_path = None
            current.updated_at = now
            return current

        if self._call_repo.update(business_id, call.id, forget) is None:
            return discarded(0)

        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business_id,
                action=AuditAction.DELETE,
                entity=CALL_RECORDING_ENTITY,
                entity_id=AuditEntityReference(str(call.id)),
                created_at=now,
                updated_at=now,
            )
        )
        return discarded(1)


def discarded(count: int) -> JobReport:
    return JobReport(processed_count=ProcessedItemCount(count))
