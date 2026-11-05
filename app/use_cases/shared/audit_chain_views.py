"""How the latest check of an audit hash chain is shown (cabinet and admin)."""

from app.contracts.repositories.audit_chain_repositories import (
    AuditChainRepoContract,
)
from app.schemas.domain.audit_chain import (
    AuditChainCheckpointDocument,
    AuditChainStatusDocument,
)
from app.schemas.dto.audit_chain_views import AuditChainStatusView
from app.schemas.typings.compliance.constrained_strings import AuditChainKey


def read_chain_status(
    chain_repo: AuditChainRepoContract, chain_key: AuditChainKey
) -> AuditChainStatusView:
    """The latest check of a chain and where a purge last cut it."""

    return chain_status_view(
        chain_repo.status_of(chain_key), chain_repo.checkpoint_of(chain_key)
    )


def chain_status_view(
    status: AuditChainStatusDocument | None,
    checkpoint: AuditChainCheckpointDocument | None,
) -> AuditChainStatusView:
    purged_through = None if checkpoint is None else checkpoint.through_position
    if status is None:
        return AuditChainStatusView(purged_through_position=purged_through)

    return AuditChainStatusView(
        status=status.status,
        problem=status.problem,
        broken_position=status.broken_position,
        verified_through_position=status.verified_through_position,
        purged_through_position=purged_through,
        entries_checked=status.entries_checked,
        checked_at=status.checked_at,
    )
