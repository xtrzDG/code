"""
What the cabinet shows of the audit log's hash chains: the latest check of
a business's chain on its Audit tab, and the platform admin's audit view
(the platform's own entries and the chains found broken).
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.compliance import (
    AuditAction,
    AuditChainProblem,
    AuditChainStatus,
    AuditSecurityEvent,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import (
    AuditChainCount,
    AuditChainEntryCount,
    AuditChainPosition,
    AuditRecordCount,
)
from app.schemas.typings.compliance.prefixed_id import AuditLogEntryId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId


class AuditChainStatusQuery(ImmutableDTO):
    """An owner asks how the latest check of the business's chain went."""

    user_id: UserId
    business_id: BusinessId


class AuditChainStatusView(ImmutableDTO):
    """
    What the latest daily check of one chain found. `status` is None until
    the first check ran; `verified_through_position` is the newest entry a
    check verified, `purged_through_position` the last one a purge removed
    (the chain then starts after it).
    """

    status: AuditChainStatus | None = None
    problem: AuditChainProblem | None = None
    broken_position: AuditChainPosition | None = None
    verified_through_position: AuditChainPosition | None = None
    purged_through_position: AuditChainPosition | None = None
    entries_checked: AuditChainEntryCount = AuditChainEntryCount(0)
    checked_at: Microseconds | None = None


class BrokenAuditChainView(ImmutableDTO):
    """A chain the latest check found broken (`business_id` None: the platform's)."""

    business_id: BusinessId | None = None
    problem: AuditChainProblem | None = None
    broken_position: AuditChainPosition | None = None
    checked_at: Microseconds


class AdminAuditChainsQuery(ImmutableDTO):
    """A platform admin asks how the checks of every chain went."""

    user_id: UserId


class AuditChainOverview(ImmutableDTO):
    """
    The platform's own chain, how many chains the latest checks found
    intact and broken, and the broken ones (at most 50).
    """

    platform: AuditChainStatusView
    intact_chains: AuditChainCount
    broken_chains: AuditChainCount
    broken: list[BrokenAuditChainView] = Field(
        default_factory=list[BrokenAuditChainView]
    )


class PlatformAuditLogQuery(ImmutableDTO):
    """
    A platform admin reads the entries that name no business (sign-ins and
    their failures, sign-outs, two-factor changes, the admin team, key
    rotations, platform purges), newest first, one page at a time,
    optionally of one operation or security event.
    """

    user_id: UserId
    page: PageRequest = PageRequest()
    action: AuditAction | None = None
    security_event: AuditSecurityEvent | None = None


class PlatformAuditEntryView(ImmutableDTO):
    """One entry of the platform's chain, at its position."""

    id: AuditLogEntryId
    chain_position: AuditChainPosition | None = None
    action: AuditAction
    security_event: AuditSecurityEvent | None = None
    entity: AuditEntityName
    entity_id: AuditEntityReference | None = None
    actor_id: UserId | None = None
    ip_address: ClientIpAddress | None = None
    occurred_at: Microseconds
    record_count: AuditRecordCount | None = None


class PlatformAuditLogPage(ImmutableDTO):
    """One page of the platform's entries; `next_cursor` is None on the last."""

    items: list[PlatformAuditEntryView]
    next_cursor: PageCursor | None = None
