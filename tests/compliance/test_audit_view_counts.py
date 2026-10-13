"""
The audit log stays readable: the same view of the same list by the same
person from the same address within 5 minutes is one entry with a count.
The count lives beside the hash chain (`audit_view_counts`): the entry
itself is never changed, so its hash still holds.
"""

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.prefixed_id import AuditLogEntryId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.compliance.audit_chain_hashing import compute_entry_hash
from tests.compliance.audit_repositories import audit_log_repository

MINUTE: int = 60 * 1_000_000
START: int = 1_790_000_000_000_000
BUSINESS: BusinessId = BusinessId()
OWNER: UserId = UserId()


def view(
    minute: float,
    *,
    entity: str = "booking",
    record: str | None = None,
    ip: str | None = "198.51.100.7",
    actor: UserId | None = OWNER,
    action: AuditAction = AuditAction.VIEW,
) -> AuditLogEntryDocument:
    at = Microseconds(START + int(minute * MINUTE))
    return AuditLogEntryDocument(
        business_id=BUSINESS,
        actor_id=actor,
        action=action,
        entity=AuditEntityName(entity),
        entity_id=None if record is None else AuditEntityReference(record),
        ip_address=None if ip is None else ClientIpAddress(ip),
        created_at=at,
        updated_at=at,
    )


def stored_log(*entries: AuditLogEntryDocument) -> list[tuple[int | None, int]]:
    """Each stored entry's own record count and how many views it stands for."""

    log = audit_log_repository(InMemoryDocumentCollectionAdapter(AuditLogEntryDocument))
    for entry in entries:
        log.append(entry)
    stored = log.list_by_business(BUSINESS)
    for entry in stored:
        assert entry.entry_hash == compute_entry_hash(entry)
    views: dict[AuditLogEntryId, int] = {
        entry_id: int(count)
        for entry_id, count in log.view_counts(
            BUSINESS, [entry.id for entry in stored]
        ).items()
    }
    return [
        (
            None if entry.record_count is None else int(entry.record_count),
            views.get(entry.id, 1),
        )
        for entry in stored
    ]


def counts(entries: list[tuple[int | None, int]]) -> list[int]:
    return [views for _, views in entries]


def test_repeated_views_within_five_minutes_are_one_entry() -> None:
    entries = stored_log(view(0), view(2), view(4.5))

    assert counts(entries) == [3]
    assert entries[0][0] is None, "the chained entry itself is never changed"


def test_a_view_after_five_minutes_starts_a_new_entry() -> None:
    entries = stored_log(view(0), view(6), view(7))

    assert counts(entries) == [1, 2]


def test_different_views_stay_apart() -> None:
    entries = stored_log(
        view(0),
        view(1, ip="203.0.113.9"),
        view(1, entity="lead"),
        view(1, record="booking_42"),
        view(1, actor=UserId()),
        view(1, actor=None),
        view(1, actor=None),
    )

    assert counts(entries) == [1] * 7


def test_only_views_are_counted() -> None:
    entries = stored_log(
        view(0, action=AuditAction.EXPORT), view(1, action=AuditAction.EXPORT)
    )

    assert counts(entries) == [1, 1]
