from typed_time_provider import Microseconds, WallClock

from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import CallRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import CallDocument
from app.schemas.dto.call_recordings import (
    CallRecordingArchiveJobPayload,
    CallRecordingMove,
    RecordingAudio,
    RecordingLocation,
    RecordingPart,
)
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.voice.recordings.recording_archive_paths import (
    build_archived_recording_path,
)
from app.utilities.channels.voice_recordings import (
    build_voice_platform_recording_path,
    read_voice_platform_call_id,
)

CALL_RECORDING_ENTITY: AuditEntityName = AuditEntityName("call_recording")


class ArchiveCallRecordingUseCase(UseCaseContract[QueuedJobInput, JobReport]):
    """
    Queued job "archive_call_recording": copy a call's recording from the
    voice platform into the platform's EU object storage (sealed with the
    business's key), point the call at the copy, then delete the voice
    platform's conversation (its audio and transcript; the call keeps its
    own transcript). From then on playback, retention and erasure work on
    the archived copy, and no processor keeps a second one.

    Idempotent and safe against the other writers of the call: the call is
    pointed at the copy only while it still points at the platform's
    recording; when a retention purge or a contact's erasure cleared it in
    between, the copy is deleted again. A retry after the move only makes
    sure the platform's copy is gone. The move is written to the audit log.
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
            raise ValidationFailedError("A recording archive job names no business.")

        payload = CallRecordingArchiveJobPayload.model_validate_json(
            str(input_data.payload)
        )
        call: CallDocument | None = self._call_repo.get(business_id, payload.call_id)
        if call is None or call.recording_path is None:
            return archived(0)

        if read_voice_platform_call_id(call.recording_path) is None:
            self._delete_platform_copy(call)
            return archived(0)

        platform_copy = RecordingLocation(
            business_id=business_id, path=call.recording_path
        )
        whole: RecordingPart | None = self._recording_storage.read(platform_copy)
        if whole is None:
            return archived(0)

        archived_path: RecordingStoragePath = build_archived_recording_path(
            business_id, call.id, whole.media_type
        )
        archive = RecordingLocation(business_id=business_id, path=archived_path)
        self._recording_storage.store(
            archive, RecordingAudio(content=whole.content, media_type=whole.media_type)
        )
        now: Microseconds = self._wall_clock.now_unix()
        is_moved: bool = self._call_repo.move_recording(
            business_id,
            call.id,
            CallRecordingMove(
                from_path=call.recording_path, to_path=archived_path, moved_at=now
            ),
        )
        if not is_moved:
            self._recording_storage.delete(archive)
            return archived(0)

        self._recording_storage.delete(platform_copy)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business_id,
                action=AuditAction.UPDATE,
                entity=CALL_RECORDING_ENTITY,
                entity_id=AuditEntityReference(str(call.id)),
                created_at=now,
                updated_at=now,
            )
        )
        return archived(1)

    def _delete_platform_copy(self, call: CallDocument) -> None:
        self._recording_storage.delete(
            RecordingLocation(
                business_id=call.business_id,
                path=build_voice_platform_recording_path(call.provider_call_id),
            )
        )


def archived(count: int) -> JobReport:
    return JobReport(processed_count=ProcessedItemCount(count))
