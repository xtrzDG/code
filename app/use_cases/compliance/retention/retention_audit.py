"""The audit entries of one retention purge of a business: one per kind."""

from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.retention_purges import RetentionPurgeCounts
from app.schemas.dto.retention import RetentionWindow
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import AuditRecordCount
from app.schemas.typings.compliance.strings import AuditEntityName

# The audit entity of each count (the names other purges and the erasure
# use for the same records, so the cabinet's audit filter groups them).
PURGED_ENTITIES: tuple[tuple[str, str], ...] = (
    ("messages", "deleted_messages"),
    ("llm_turns", "deleted_llm_turns"),
    ("conversation_note", "deleted_notes"),
    ("message_media", "deleted_media"),
    ("missed_call", "deleted_missed_calls"),
    ("call", "erased_calls"),
    ("lead", "anonymized_leads"),
    ("booking", "anonymized_bookings"),
    ("handoff", "anonymized_handoffs"),
)


def retention_audit_entries(
    business_id: BusinessId, counts: RetentionPurgeCounts, now: Microseconds
) -> list[AuditLogEntryDocument]:
    """
    RETENTION_PURGE of each kind of record the purge removed, with how many
    (no actor: the platform did it; no ids: nothing personal).
    """

    entries: list[AuditLogEntryDocument] = []
    for entity, count_field in PURGED_ENTITIES:
        count: int = int(getattr(counts, count_field))
        if count > 0:
            entries.append(
                AuditLogEntryDocument(
                    business_id=business_id,
                    action=AuditAction.RETENTION_PURGE,
                    entity=AuditEntityName(entity),
                    record_count=AuditRecordCount(count),
                    created_at=now,
                    updated_at=now,
                )
            )

    return entries


def window_since(
    purged_before: Microseconds | None, cutoff: Microseconds
) -> RetentionWindow | None:
    """
    What went past retention since the previous purge (from its cutoff to
    this one's); None when nothing did (the period was made longer).
    """

    if purged_before is not None and int(purged_before) >= int(cutoff):
        return None

    return RetentionWindow(since=purged_before, before=cutoff)
