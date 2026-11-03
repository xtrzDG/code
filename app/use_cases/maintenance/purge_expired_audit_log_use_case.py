import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.audit_trail import AuditLogPurgeCommand, AuditLogPurgeReport
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.compliance.constrained_integers import AuditPurgeBatchSize
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.utilities.compliance.audit_retention import (
    AUDIT_LOG_RETENTION_DAYS,
    retention_cutoff,
)

logger: logging.Logger = logging.getLogger(__name__)
# Entries per statement: one short transaction each, the chain's lock held
# only for it.
SCHEDULED_PURGE_BATCH: AuditPurgeBatchSize = AuditPurgeBatchSize(1_000)


class PurgeExpiredAuditLogUseCase(UseCaseContract[JobTick, JobReport]):
    """
    The daily `purge_expired_audit_log` job (PRIV-07): the audit and
    security log is kept 1,095 days, so each run removes from the
    platform's chain and every business's the entries written before the
    run's moment minus the retention. It runs the operator's purge
    (`workshop purge-audit-log`, `PurgeAuditLogUseCase`) on the database's
    retention purge (`workshop.purge_expired_audit_chain`, migration 1250),
    which removes nothing younger than the retention by the database's own
    clock and keeps every chain verifiable with its checkpoint. Each chain
    that lost entries gets its RETENTION_PURGE entry; a second run on the
    same day finds nothing more to remove. The report counts the entries
    removed.
    """

    def __init__(
        self,
        purge_audit_log: UseCaseContract[AuditLogPurgeCommand, AuditLogPurgeReport],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._purge_audit_log: UseCaseContract[
            AuditLogPurgeCommand, AuditLogPurgeReport
        ] = purge_audit_log
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        report: AuditLogPurgeReport = self._purge_audit_log.run(
            AuditLogPurgeCommand(
                created_before=retention_cutoff(self._wall_clock.now_unix()),
                batch_size=SCHEDULED_PURGE_BATCH,
            )
        )
        if int(report.entries_removed) > 0:
            logger.info(
                "Audit log retention (%d days): %d entries removed from %d chains.",
                int(AUDIT_LOG_RETENTION_DAYS),
                int(report.entries_removed),
                int(report.chains_purged),
            )

        return JobReport(
            processed_count=ProcessedItemCount(int(report.entries_removed))
        )
