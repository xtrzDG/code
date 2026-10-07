"""
The audit log stays readable: the same view of the same list by the same
person from the same address within 5 minutes is one entry with a count.
"""

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.compliance_repositories import AuditLogRepository
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.users.prefixed_id import UserId

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


def stored_log(*entries: AuditLogEntryDocument) -> list[AuditLogEntryDocument]:
    log = AuditLogRepository(InMemoryDocumentCollectionAdapter(AuditLogEntryDocument))
    for entry in entries:
        log.append(entry)
    return log.list_by_business(BUSINESS)


def counts(entries: list[AuditLogEntryDocument]) -> list[int | None]:
    return [
        None if entry.record_count is None else int(entry.record_count)
        for entry in entries
    ]


def test_repeated_views_within_five_minutes_are_one_entry() -> None:
    entries = stored_log(view(0), view(2), view(4.5))

    assert counts(entries) == [3]
    assert int(entries[0].created_at) == START
    assert int(entries[0].updated_at) == START + int(4.5 * MINUTE)


def test_a_view_after_five_minutes_starts_a_new_entry() -> None:
    entries = stored_log(view(0), view(6), view(7))

    assert counts(entries) == [None, 2]


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

    assert counts(entries) == [None] * 7


def test_only_views_are_counted() -> None:
    entries = stored_log(
        view(0, action=AuditAction.EXPORT), view(1, action=AuditAction.EXPORT)
    )

    assert counts(entries) == [None, None]
