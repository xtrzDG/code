import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.support_access import SupportAccessGrantRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import SupportAccessEndReason
from app.schemas.domain.support_access_grants import SupportAccessGrantDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.support_access import SupportAccessEnding
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.shared.support_access import end_grant

logger: logging.Logger = logging.getLogger(__name__)


class EndExpiredSupportAccessUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Periodic job over every business: grants whose time is up are ended
    (EXPIRED), each support look audited as SUPPORT_ACCESS_END (no actor:
    time ended it) and each lapsed consent as an UPDATE of the write
    access, so the audit log closes every access it opened. The access
    check refuses an expired grant at once, with or without this job;
    running it twice ends nothing twice (compare-and-swap).
    """

    def __init__(
        self,
        grant_repo: SupportAccessGrantRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._grant_repo: SupportAccessGrantRepoContract = grant_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        ended: int = 0
        for grant in self._grant_repo.list_open_everywhere():
            if int(grant.expires_at) > int(now):
                continue

            try:
                ended += int(self._end(grant) is not None)
            except Exception:
                logger.exception("Support access %s was not ended.", grant.id)

        return JobReport(processed_count=ProcessedItemCount(ended))

    def _end(
        self, grant: SupportAccessGrantDocument
    ) -> SupportAccessGrantDocument | None:
        return end_grant(
            self._grant_repo,
            self._audit_log_repo,
            grant,
            SupportAccessEnding(
                ended_at=grant.expires_at,
                reason=SupportAccessEndReason.EXPIRED,
            ),
            client_ip_address=None,
        )
