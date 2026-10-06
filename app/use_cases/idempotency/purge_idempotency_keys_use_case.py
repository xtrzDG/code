from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.idempotency_repositories import (
    IdempotencyKeyRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.storage.constrained_integers import DocumentCount

IDEMPOTENCY_KEY_ENTITY: AuditEntityName = AuditEntityName("idempotency_key")


class PurgeIdempotencyKeysUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Hourly: delete the idempotency key records whose day ran out, and those
    released by a failed request, so a stored answer (it may hold a
    customer's name or number) never outlives its key by more than an hour.
    A purge that removed records is audited as RETENTION_PURGE, without an
    actor or a business; running it twice is harmless.
    """

    def __init__(
        self,
        idempotency_key_repo: IdempotencyKeyRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._idempotency_key_repo: IdempotencyKeyRepoContract = idempotency_key_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        purged: DocumentCount = self._idempotency_key_repo.delete_expired_before(now)
        if int(purged) > 0:
            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    action=AuditAction.RETENTION_PURGE,
                    entity=IDEMPOTENCY_KEY_ENTITY,
                    created_at=now,
                    updated_at=now,
                )
            )

        return JobReport(processed_count=ProcessedItemCount(int(purged)))
