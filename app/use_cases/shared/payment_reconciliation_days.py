"""The latest daily payment reconciliation: today's (UTC), else yesterday's."""

from typed_time_provider import Microseconds

from app.contracts.platform_safety import PaymentReconciliationRepoContract
from app.schemas.domain.payment_reconciliations import PaymentReconciliationDocument
from app.schemas.typings.billing.constrained_strings import ReconciliationDay
from app.utilities.spend.spend_days import DAY_MICROSECONDS, utc_day


def reconciliation_day(now: Microseconds) -> ReconciliationDay:
    """The UTC day a run at `now` is stored under."""

    return ReconciliationDay(str(utc_day(now)[0]))


def latest_reconciliation(
    reconciliation_repo: PaymentReconciliationRepoContract, now: Microseconds
) -> PaymentReconciliationDocument | None:
    for moment in (int(now), int(now) - DAY_MICROSECONDS):
        found: PaymentReconciliationDocument | None = reconciliation_repo.get(
            reconciliation_day(Microseconds(moment))
        )
        if found is not None:
            return found

    return None
