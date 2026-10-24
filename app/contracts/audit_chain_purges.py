"""Removing the oldest entries of an audit hash chain without breaking it."""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.adapter_contract import AdapterContract
from app.schemas.typings.compliance.constrained_integers import (
    AuditChainEntryCount,
    AuditPurgeBatchSize,
)
from app.schemas.typings.compliance.constrained_strings import AuditChainKey


class AuditChainPurgeAdapterContract(AdapterContract, Protocol):
    def purge(
        self,
        chain_key: AuditChainKey,
        created_before: Microseconds,
        max_entries: AuditPurgeBatchSize,
    ) -> AuditChainEntryCount:
        """
        Remove at most `max_entries` of the chain's oldest entries written
        before `created_before` (a prefix: up to the first entry written at
        or after it) and as many of its entries from before the chain, and
        record the chain's checkpoint (the last removed position and its
        hash), under the chain's advisory lock in one transaction. Returns
        how many entries went; 0 when nothing is left to remove.
        """
        raise NotImplementedError
