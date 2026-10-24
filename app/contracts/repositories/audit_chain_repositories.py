"""
Persistence contracts of the audit log's hash chains: what their check
reads and keeps, and what the platform's audit view and the anomaly
alerts read across businesses.

Implementations return independent copies: mutating a returned document
does not change stored state until it is saved.
"""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.constants.compliance import AuditAction, AuditChainStatus
from app.schemas.domain.audit_chain import (
    AuditChainCheckpointDocument,
    AuditChainStatusDocument,
)
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.audit_trail import (
    AdminTenantCount,
    BusinessOperationCount,
    FailedCheckCount,
    PlatformAuditFilter,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.compliance.constrained_integers import AuditChainPosition
from app.schemas.typings.compliance.constrained_strings import AuditChainKey
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentQueryLimit,
)


class AuditChainRepoContract(RepoContract, Protocol):
    def head_of(self, chain_key: AuditChainKey) -> AuditLogEntryDocument | None:
        """The newest entry of a chain; None when it holds none."""
        raise NotImplementedError

    def entries_from(
        self,
        chain_key: AuditChainKey,
        position: AuditChainPosition,
        limit: DocumentQueryLimit,
    ) -> list[AuditLogEntryDocument]:
        """A chain's entries from `position` on, by position, at most `limit`."""
        raise NotImplementedError

    def checkpoint_of(
        self, chain_key: AuditChainKey
    ) -> AuditChainCheckpointDocument | None:
        """Where a purge last cut the chain; None when nothing was purged."""
        raise NotImplementedError

    def status_of(self, chain_key: AuditChainKey) -> AuditChainStatusDocument | None:
        raise NotImplementedError

    def save_status(self, status: AuditChainStatusDocument) -> None:
        raise NotImplementedError

    def count_by_status(self) -> dict[AuditChainStatus, DocumentCount]:
        """How many chains the latest checks found intact and broken."""
        raise NotImplementedError

    def list_broken(self, limit: DocumentQueryLimit) -> list[AuditChainStatusDocument]:
        """Chains the latest check found broken, at most `limit` of them."""
        raise NotImplementedError


class AuditActivityRepoContract(RepoContract, Protocol):
    def page_platform_entries(
        self,
        window: KeysetSlice,
        log_filter: PlatformAuditFilter,
    ) -> list[AuditLogEntryDocument]:
        """
        The platform's own entries (those that name no business: its
        chain's and those written before the chain), newest first: one
        keyset page by the time they were written.
        """
        raise NotImplementedError

    def count_personal_data_operations(
        self, since: Microseconds
    ) -> list[BusinessOperationCount]:
        """
        Exports of personal data (an EXPORT of a contact, a segment, a
        list with customers or staff in it, or the whole business; never an
        invoice or receipt PDF) and erasures (DELETE of a contact) since
        `since`, per business that ran any.
        """
        raise NotImplementedError

    def count_tenants_by_admin(
        self,
        since: Microseconds,
        actions: Sequence[AuditAction],
    ) -> list[AdminTenantCount]:
        """
        How many different businesses each person entered or changed with
        one of `actions` (the platform admins' own) since `since`.
        """
        raise NotImplementedError

    def count_failed_checks(self, since: Microseconds) -> list[FailedCheckCount]:
        """
        Failed sign-in checks (wrong codes and the lockouts they caused)
        since `since`, per destination.
        """
        raise NotImplementedError
