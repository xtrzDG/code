from typed_time_provider import Microseconds, WallClock

from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.contracts.repositories import AuditLogRepoContract, CallRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import CallDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.call_recordings import CallRecordingQuery, RecordingAudio
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)

CALL_RECORDING_ENTITY: AuditEntityName = AuditEntityName("call_recording")
NO_RECORDING_MESSAGE: str = (
    "This call has no recording: the caller did not agree to it, or it was "
    "deleted after the retention period."
)


class GetCallRecordingUseCase(UseCaseContract[CallRecordingQuery, RecordingAudio]):
    """
    Owners and staff play back the recording of a phone call from the
    conversation card (concept sections 7 and 8). The audio stays with the
    voice platform (ElevenLabs keeps it in the EU) or the recording storage
    and is read only when someone presses play; each playback is a view of
    personal data and is written to the audit log (concept section 10), once
    (the parts a player asks for while it plays and seeks are not new
    playbacks; access is checked for every one of them).

    A call of another business, a call without a recording (no consent,
    purged after the retention period, deleted with the contact's data) and
    a recording the storage no longer has are all NotFoundError.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        call_repo: CallRepoContract,
        recording_storage: RecordingStorageAdapterContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._call_repo: CallRepoContract = call_repo
        self._recording_storage: RecordingStorageAdapterContract = recording_storage
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CallRecordingQuery) -> RecordingAudio:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        call: CallDocument | None = self._call_repo.get(business.id, input_data.call_id)
        if call is None:
            raise NotFoundError(f"Call {input_data.call_id} was not found.")

        if call.recording_path is None:
            raise NotFoundError(NO_RECORDING_MESSAGE)

        audio: RecordingAudio | None = self._recording_storage.read(call.recording_path)
        if audio is None:
            raise NotFoundError(NO_RECORDING_MESSAGE)

        if not input_data.starts_playback:
            # A later part of a playback that is already in the audit log.
            return audio

        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.VIEW,
                entity=CALL_RECORDING_ENTITY,
                entity_id=AuditEntityReference(str(call.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return audio
