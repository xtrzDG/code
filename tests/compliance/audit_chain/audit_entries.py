"""Audit entries for the hash chain tests."""

from typed_time_provider import Microseconds, WallClock

from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.users.prefixed_id import UserId

START: int = 1_790_000_000_000_000
MINUTE: int = 60 * 1_000_000
# Two years, in minutes: a purge may remove what was written that long ago.
TWO_YEARS_IN_MINUTES: int = 2 * 365 * 24 * 60
TWO_YEARS_LATER: int = START + TWO_YEARS_IN_MINUTES * MINUTE


def entry(
    business_id: BusinessId | None,
    minute: float = 0,
    *,
    action: AuditAction = AuditAction.EXPORT,
    entity: str = "contact",
    record: str | None = None,
    actor: UserId | None = None,
) -> AuditLogEntryDocument:
    at = Microseconds(START + int(minute * MINUTE))
    return AuditLogEntryDocument(
        business_id=business_id,
        actor_id=actor,
        action=action,
        entity=AuditEntityName(entity),
        entity_id=None if record is None else AuditEntityReference(record),
        ip_address=ClientIpAddress("198.51.100.7"),
        created_at=at,
        updated_at=at,
    )


def wall_clock_at(unix_microseconds: int) -> WallClock[Microseconds]:
    """A clock standing still at `unix_microseconds`."""

    return WallClock(
        preferred_time_unit_type=Microseconds,
        unix_nanosecond_factory=lambda: unix_microseconds * 1_000,
    )
