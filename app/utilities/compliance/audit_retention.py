"""
How long audit entries are kept at least, and so which purges are allowed.

A purge removes only entries written before its cutoff, and a cutoff must
lie at least the minimum retention before the moment the purge runs. The
database's purge function (`workshop.purge_audit_chain`, migration 1193)
refuses a newer cutoff itself and stores the cutoff in the chain's
checkpoint; the chain's check accepts a checkpoint over the newest entry
it verified only when that cutoff is old enough (else HEAD_LOST).
"""

from typed_time_provider import Microseconds

from app.schemas.typings.compliance.constrained_integers import AuditRetentionDays

MINIMUM_AUDIT_RETENTION_DAYS: AuditRetentionDays = AuditRetentionDays(365)
MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000


def newest_allowed_cutoff(now: Microseconds) -> Microseconds:
    """The newest cutoff a purge may use at `now`."""

    return Microseconds(
        int(now) - int(MINIMUM_AUDIT_RETENTION_DAYS) * MICROSECONDS_PER_DAY
    )


def is_cutoff_allowed(cutoff: Microseconds, now: Microseconds) -> bool:
    """Whether a purge at `now` may remove entries written before `cutoff`."""

    return int(cutoff) <= int(newest_allowed_cutoff(now))
