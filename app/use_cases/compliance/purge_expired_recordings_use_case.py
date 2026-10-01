from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.contracts.repositories import (
    AuditLogRepoContract,
    BusinessRepoContract,
    CallRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.compliance import (
    PurgeExpiredRecordingsCommand,
    RecordingPurgeResult,
)
from app.schemas.typings.compliance.constrained_integers import (
    DeletedRecordingCount,
    PurgedCallCount,
    ScannedBusinessCount,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)

SECONDS_PER_DAY: int = 24 * 60 * 60


class PurgeExpiredRecordingsUseCase(
    UseCaseContract[PurgeExpiredRecordingsCommand, RecordingPurgeResult]
):
    """
    Background retention job: remove old call recordings and transcripts.

    For every business (or the one given), calls that started more than its
    `recording_retention_days` ago lose their recording (deleted from storage)
    and transcript; the call record itself stays for statistics. Each purged
    call is audited as RETENTION_PURGE without an actor. Running it twice is
    harmless.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        call_repo: CallRepoContract,
        recording_storage: RecordingStorageAdapterContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._call_repo: CallRepoContract = call_repo
        self._recording_storage: RecordingStorageAdapterContract = recording_storage
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PurgeExpiredRecordingsCommand) -> RecordingPurgeResult:
        businesses: list[BusinessDocument] = self._select_businesses(input_data)
        purged_calls: int = 0
        deleted_recordings: int = 0
        for business in businesses:
            business_purged_calls, business_deleted_recordings = self._purge_business(
                business
            )
            purged_calls += business_purged_calls
            deleted_recordings += business_deleted_recordings

        return RecordingPurgeResult(
            scanned_businesses=ScannedBusinessCount(len(businesses)),
            purged_calls=PurgedCallCount(purged_calls),
            deleted_recordings=DeletedRecordingCount(deleted_recordings),
        )

    def _select_businesses(
        self,
        input_data: PurgeExpiredRecordingsCommand,
    ) -> list[BusinessDocument]:
        if input_data.business_id is None:
            return self._business_repo.list_all()

        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        return [] if business is None else [business]

    def _purge_business(self, business: BusinessDocument) -> tuple[int, int]:
        now: Microseconds = self._wall_clock.now_unix()
        retention_cutoff: Microseconds = self._wall_clock.now_unix_with_delta(
            Seconds(-int(business.recording_retention_days) * SECONDS_PER_DAY)
        )
        purged_calls: int = 0
        deleted_recordings: int = 0
        for call in self._call_repo.list_by_business(business.id):
            is_expired: bool = call.started_at < retention_cutoff
            has_content: bool = (
                call.recording_path is not None or call.transcript is not None
            )
            if not is_expired or not has_content:
                continue

            if call.recording_path is not None:
                self._recording_storage.delete(call.recording_path)
                deleted_recordings += 1

            call.recording_path = None
            call.transcript = None
            call.updated_at = now
            self._call_repo.save(call)
            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    business_id=business.id,
                    action=AuditAction.RETENTION_PURGE,
                    entity=AuditEntityName("call"),
                    entity_id=AuditEntityReference(str(call.id)),
                    created_at=now,
                    updated_at=now,
                )
            )
            purged_calls += 1

        return purged_calls, deleted_recordings
