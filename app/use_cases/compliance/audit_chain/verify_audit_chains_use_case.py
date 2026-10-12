import logging
from collections.abc import Iterator

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.audit_chain_repositories import (
    AuditChainRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditChainStatus
from app.schemas.domain.audit_chain import AuditChainStatusDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.compliance.constrained_strings import AuditChainKey
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.compliance.audit_chain.audit_chain_verification import (
    AuditChainVerification,
)
from app.use_cases.shared.business_walk import walk_businesses
from app.utilities.compliance.audit_chain_hashing import (
    PLATFORM_CHAIN_KEY,
    chain_key_of,
)

logger: logging.Logger = logging.getLogger(__name__)


class VerifyAuditChainsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    The daily `verify_audit_chain` job: checks the platform's chain and
    every business's (`AuditChainVerification`) and stores what each check
    found, for the Audit tab, the admin audit view and the
    AUDIT_CHAIN_BROKEN alert.

    Every chain that grew since its last check is logged with its newest
    verified position and hash: the log drain keeps a copy of each head
    outside the database, so an end of a chain rewritten with fresh hashes
    still disagrees with the log. The lines name chains and hashes only,
    never a person. The report counts the chains checked.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        chain_repo: AuditChainRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._chain_repo: AuditChainRepoContract = chain_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        verification = AuditChainVerification(self._chain_repo)
        checked: int = 0
        for chain_key in self._chains():
            previous: AuditChainStatusDocument | None = self._chain_repo.status_of(
                chain_key
            )
            status: AuditChainStatusDocument = verification.verify(
                chain_key, previous, self._wall_clock.now_unix()
            )
            self._chain_repo.save_status(status)
            report_check(previous, status)
            checked += 1

        return JobReport(processed_count=ProcessedItemCount(checked))

    def _chains(self) -> Iterator[AuditChainKey]:
        yield PLATFORM_CHAIN_KEY
        for business in walk_businesses(self._business_repo):
            yield chain_key_of(business.id)


def report_check(
    previous: AuditChainStatusDocument | None, status: AuditChainStatusDocument
) -> None:
    """Log a broken chain, and the new head of a chain that grew."""

    if status.status is AuditChainStatus.BROKEN:
        logger.error(
            "Audit chain %s is broken at position %s: %s.",
            status.id,
            int(status.broken_position or 0),
            None if status.problem is None else status.problem.value,
        )
        return

    if status.verified_through_position is not None and (
        previous is None
        or previous.verified_through_position != status.verified_through_position
    ):
        logger.info(
            "Audit chain %s verified through position %s, hash %s.",
            status.id,
            int(status.verified_through_position),
            status.verified_through_hash,
        )
