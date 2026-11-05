"""What one check of an audit hash chain found, as the status it stores."""

from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditChainStatus
from app.schemas.domain.audit_chain import AuditChainStatusDocument
from app.schemas.typings.compliance.constrained_integers import AuditChainPosition
from app.schemas.typings.compliance.constrained_strings import (
    AuditChainKey,
    AuditEntryHash,
)
from app.use_cases.compliance.audit_chain.audit_chain_walk import (
    ChainFinding,
    ChainWalk,
)
from app.utilities.compliance.audit_chain_hashing import business_of_chain


def chain_status(
    chain_key: AuditChainKey,
    previous: AuditChainStatusDocument | None,
    walk: ChainWalk,
    finding: ChainFinding | None,
    now: Microseconds,
) -> AuditChainStatusDocument:
    """
    The chain's status after a walk: INTACT through the newest entry ever
    verified, or BROKEN at the finding. A walk that stopped before the
    chain's newest entry resumes after its last verified one next time.
    """

    through_position: AuditChainPosition | None = (
        None if previous is None else previous.verified_through_position
    )
    through_hash: AuditEntryHash | None = (
        None if previous is None else previous.verified_through_hash
    )
    if (
        finding is None
        and walk.last is not None
        and (
            through_position is None
            or int(walk.last.chain_position or 0) >= int(through_position)
        )
    ):
        through_position = walk.last.chain_position
        through_hash = walk.last.entry_hash

    return AuditChainStatusDocument(
        id=chain_key,
        business_id=business_of_chain(chain_key),
        status=(
            AuditChainStatus.INTACT if finding is None else AuditChainStatus.BROKEN
        ),
        problem=None if finding is None else finding.problem,
        broken_position=None if finding is None else finding.position,
        verified_through_position=through_position,
        verified_through_hash=through_hash,
        resume_position=(
            None if finding is not None or walk.reached_head else walk.position
        ),
        entries_checked=walk.checked,
        checked_at=now,
        created_at=now if previous is None else previous.created_at,
        updated_at=now,
    )
