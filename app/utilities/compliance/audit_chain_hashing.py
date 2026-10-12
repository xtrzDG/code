"""
The audit log's hash chains: which chain an entry belongs to, its
canonical JSON and its hash.

Each business's entries form one chain and the entries that name no
business form the platform's. An entry's hash is the SHA-256 of its
canonical JSON: the fields below, the chain and position, and the hash of
the entry before it (64 zeros for the first), with sorted keys, no spaces
and UTF-8. Changing a stored entry changes its hash; removing or putting in
an entry breaks the link of the one after it.

The hashed fields are fixed (format 1): a field the entry gains later joins
the hash only with a new format, so an upcaster that fills a new field on
read never changes the hash of an old entry.
"""

import hashlib
import json

from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import AuditChainPosition
from app.schemas.typings.compliance.constrained_strings import (
    AuditChainKey,
    AuditEntryHash,
)
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey

PLATFORM_CHAIN_KEY: AuditChainKey = AuditChainKey("platform")
GENESIS_HASH: AuditEntryHash = AuditEntryHash("0" * 64)
HASH_FORMAT: int = 1
FIRST_POSITION: AuditChainPosition = AuditChainPosition(1)
# The advisory lock of one chain: its appends and the database's purge
# function (migration 1193) take the same key.
CHAIN_LOCK_PURPOSE: str = "audit_chain"


def chain_key_of(business_id: BusinessId | None) -> AuditChainKey:
    """The chain of a business's entries, or the platform's."""

    if business_id is None:
        return PLATFORM_CHAIN_KEY

    return AuditChainKey(str(business_id))


def chain_lock_key(chain_key: AuditChainKey) -> AdvisoryLockKey:
    """The advisory lock that orders a chain's appends and purges."""

    return AdvisoryLockKey(f"{CHAIN_LOCK_PURPOSE}|{chain_key}")


def business_of_chain(chain_key: AuditChainKey) -> BusinessId | None:
    """The business whose chain it is; None for the platform's."""

    if chain_key == PLATFORM_CHAIN_KEY:
        return None

    return BusinessId(str(chain_key))


def link_entry_and_hash(
    entry: AuditLogEntryDocument,
    position: AuditChainPosition,
    prev_hash: AuditEntryHash,
) -> tuple[AuditLogEntryDocument, AuditEntryHash]:
    """
    The entry as stored at `position` of its chain, after `prev_hash`, and
    its hash (the link of the entry after it).
    """

    chain_key: AuditChainKey = chain_key_of(entry.business_id)
    linked: AuditLogEntryDocument = entry.model_copy(
        update={
            "chain_key": chain_key,
            "chain_position": position,
            "prev_hash": prev_hash,
            "entry_hash": None,
        }
    )
    entry_hash: AuditEntryHash = compute_entry_hash(linked)
    return linked.model_copy(update={"entry_hash": entry_hash}), entry_hash


def compute_entry_hash(entry: AuditLogEntryDocument) -> AuditEntryHash:
    """
    The SHA-256 of the entry's canonical JSON, from its stored fields.

    Raises:
        ValidationFailedError: the entry holds no chain fields (written before
            the chain).
    """

    return AuditEntryHash(hashlib.sha256(canonical_entry_json(entry)).hexdigest())


def canonical_entry_json(entry: AuditLogEntryDocument) -> bytes:
    """
    The bytes an entry's hash covers.

    Raises:
        ValidationFailedError: the entry holds no chain fields.
    """

    if (
        entry.chain_key is None
        or entry.chain_position is None
        or entry.prev_hash is None
    ):
        raise ValidationFailedError(f"Audit entry {entry.id} is not in a hash chain.")

    payload: dict[str, object] = {
        "format": HASH_FORMAT,
        "chain_key": str(entry.chain_key),
        "chain_position": int(entry.chain_position),
        "prev_hash": str(entry.prev_hash),
        "id": str(entry.id),
        "business_id": text_or_none(entry.business_id),
        "actor_id": text_or_none(entry.actor_id),
        "action": entry.action.value,
        "security_event": (
            None if entry.security_event is None else entry.security_event.value
        ),
        "entity": str(entry.entity),
        "entity_id": text_or_none(entry.entity_id),
        "ip_address": text_or_none(entry.ip_address),
        "record_count": (
            None if entry.record_count is None else int(entry.record_count)
        ),
        "reason": text_or_none(entry.reason),
        "created_at": int(entry.created_at),
    }
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def text_or_none(value: object) -> str | None:
    """A typed value as its text, None as JSON null."""

    return None if value is None else str(value)
