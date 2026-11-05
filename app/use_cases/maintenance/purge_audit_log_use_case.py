import logging
from collections.abc import Iterator
from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.audit_chain_purges import AuditChainPurgeAdapterContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.audit_trail import AuditLogPurgeCommand, AuditLogPurgeReport
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.compliance.constrained_integers import (
    AuditChainCount,
    AuditChainEntryCount,
    AuditRecordCount,
)
from app.schemas.typings.compliance.constrained_strings import AuditChainKey
from app.schemas.typings.compliance.strings import AuditEntityName
from app.use_cases.shared.business_walk import walk_businesses
from app.utilities.compliance.audit_chain_hashing import (
    PLATFORM_CHAIN_KEY,
    business_of_chain,
    chain_key_of,
)
from app.utilities.compliance.audit_retention import (
    MINIMUM_AUDIT_RETENTION_DAYS,
    is_cutoff_allowed,
)

logger: logging.Logger = logging.getLogger(__name__)
AUDIT_LOG_ENTITY: AuditEntityName = AuditEntityName("audit_log_entry")


@dataclass(frozen=True)
class PurgedChain:
    """One chain that lost entries, and how many."""

    chain_key: AuditChainKey
    removed: AuditChainEntryCount


class PurgeAuditLogUseCase(UseCaseContract[AuditLogPurgeCommand, AuditLogPurgeReport]):
    """
    `workshop purge-audit-log`: remove the audit entries written before a
    cutoff from the platform's chain and every business's, a batch per
    statement, through the database's purge function
    (`AuditChainPurgeAdapterContract`): it keeps each chain verifiable
    with a checkpoint (the last removed position and its hash), so the
    daily check starts after it. Each chain that lost entries gets a
    RETENTION_PURGE entry with how many (no actor: an operator's command).
    Running it again removes nothing more.

    Raises:
        ValidationFailedError: the cutoff is younger than the minimum
            retention (the database's function refuses it too).
    """

    def __init__(
        self,
        purges: AuditChainPurgeAdapterContract,
        business_repo: BusinessRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._purges: AuditChainPurgeAdapterContract = purges
        self._business_repo: BusinessRepoContract = business_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AuditLogPurgeCommand) -> AuditLogPurgeReport:
        now: Microseconds = self._wall_clock.now_unix()
        if not is_cutoff_allowed(input_data.created_before, now):
            raise ValidationFailedError(
                "Audit entries are kept at least "
                f"{int(MINIMUM_AUDIT_RETENTION_DAYS)} days."
            )

        purged: list[PurgedChain] = []
        for chain_key in self._chains():
            removed: AuditChainEntryCount = self._purge_chain(chain_key, input_data)
            if int(removed) == 0:
                continue

            purged.append(PurgedChain(chain_key=chain_key, removed=removed))
            self._record_purge(chain_key, removed)

        return AuditLogPurgeReport(
            chains_purged=AuditChainCount(len(purged)),
            entries_removed=AuditChainEntryCount(
                sum(int(chain.removed) for chain in purged)
            ),
        )

    def _purge_chain(
        self, chain_key: AuditChainKey, command: AuditLogPurgeCommand
    ) -> AuditChainEntryCount:
        """Purge batch after batch until one removes nothing; how many went."""

        batches: list[AuditChainEntryCount] = []
        while True:
            batch: AuditChainEntryCount = self._purges.purge(
                chain_key, command.created_before, command.batch_size
            )
            if int(batch) == 0:
                return AuditChainEntryCount(sum(int(each) for each in batches))

            batches.append(batch)

    def _record_purge(
        self, chain_key: AuditChainKey, removed: AuditChainEntryCount
    ) -> None:
        """The chain's RETENTION_PURGE entry: how many entries went."""

        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business_of_chain(chain_key),
                action=AuditAction.RETENTION_PURGE,
                entity=AUDIT_LOG_ENTITY,
                record_count=AuditRecordCount(int(removed)),
                created_at=now,
                updated_at=now,
            )
        )
        logger.info("Audit chain %s: %d old entries removed.", chain_key, int(removed))

    def _chains(self) -> Iterator[AuditChainKey]:
        yield PLATFORM_CHAIN_KEY
        for business in walk_businesses(self._business_repo):
            yield chain_key_of(business.id)
