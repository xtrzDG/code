import logging
from collections.abc import Iterator

from typed_time_provider import Microseconds, WallClock

from app.contracts.billing import PaymentOrderRepoContract
from app.contracts.platform_safety import (
    PaymentReconciliationRepoContract,
    PaymentStatusReaderAdapterContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.payment_reconciliation import PaymentMismatchKind
from app.schemas.domain.payment_reconciliations import (
    PaymentMismatch,
    PaymentReconciliationDocument,
)
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.payment_reconciliation import ProviderPaymentState
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.billing.constrained_integers import ReconciledOrderCount
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.billing.payment_state_events import log_payment_mismatch
from app.use_cases.billing.reconciliation.payment_mismatch_rules import (
    find_mismatch,
    is_reconcilable,
)
from app.use_cases.shared.business_walk import walk_businesses
from app.use_cases.shared.payment_reconciliation_days import (
    reconciliation_day,
)

logger: logging.Logger = logging.getLogger(__name__)
# The most provider calls one run makes (a busy week stays within an hour).
MAX_PROVIDER_READS: int = 2_000


class ReconcilePaymentsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    The `reconcile_payments` periodic job (daily, once across workers):
    every checkout order written to within its window (`is_reconcilable`:
    the last week, a Stripe subscription's order one billing interval
    more for its renewals; the businesses walked in keyset batches, their
    orders read in each business's own storage scope: the job itself
    names no business) is compared with what Flitt or Stripe says about
    it now (`PaymentStatusReaderAdapterContract`, read-only calls). A mismatch
    that moves money (`find_mismatch`) is logged as a structured
    `payment_reconciliation_mismatch` line (ids and statuses, no card
    data) and kept in the day's result (`payment_reconciliations`), which
    the `payment_mismatch` platform alert and the admin's reconciliation
    view read. Nothing is changed: the platform admin settles a mismatch
    (docs/operations/runbooks/payment-mismatch.md).

    An order the provider cannot tell about now (it is down, it refuses
    the read, it answers unreadably) counts as unreadable and the run goes
    on; at most MAX_PROVIDER_READS orders are asked about per run, every
    question counted whatever its answer.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        payment_order_repo: PaymentOrderRepoContract,
        payment_status_reader: PaymentStatusReaderAdapterContract,
        reconciliation_repo: PaymentReconciliationRepoContract,
        storage_scope: StorageScopeContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._payment_order_repo: PaymentOrderRepoContract = payment_order_repo
        self._reader: PaymentStatusReaderAdapterContract = payment_status_reader
        self._reconciliation_repo: PaymentReconciliationRepoContract = (
            reconciliation_repo
        )
        self._storage_scope: StorageScopeContract = storage_scope
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        now: Microseconds = self._wall_clock.now_unix()
        asked: int = 0
        checked: int = 0
        unreadable: int = 0
        mismatches: list[PaymentMismatch] = []
        for order in self._recent_orders(now):
            if asked >= MAX_PROVIDER_READS:
                logger.warning(
                    "Payment reconciliation stopped after %d provider reads",
                    MAX_PROVIDER_READS,
                )
                break

            asked += 1
            try:
                state: ProviderPaymentState | None = self._reader.read_status(order)
            except ApplicationError as error:
                unreadable += 1
                logger.warning(
                    "Payment order %s could not be reconciled: %s", order.id, error
                )
                continue

            if state is None:
                continue

            checked += 1
            mismatch: PaymentMismatch | None = build_mismatch(order, state)
            if mismatch is not None:
                log_payment_mismatch(mismatch)
                mismatches.append(mismatch)

        self._reconciliation_repo.save(
            PaymentReconciliationDocument(
                day=reconciliation_day(now),
                ran_at=now,
                checked_count=ReconciledOrderCount(checked),
                unreadable_count=ReconciledOrderCount(unreadable),
                mismatches=mismatches,
                created_at=now,
                updated_at=now,
            )
        )
        logger.info(
            "Payment reconciliation: %d orders compared, %d unreadable, %d mismatches",
            checked,
            unreadable,
            len(mismatches),
        )
        return JobReport(processed_count=ProcessedItemCount(checked))

    def _recent_orders(self, now: Microseconds) -> Iterator[PaymentOrderDocument]:
        """One business's orders at a time, in the walk's order."""

        for business in walk_businesses(self._business_repo):
            with self._storage_scope.scoped_to_business(business.id):
                orders = self._payment_order_repo.list_by_business(business.id)
            yield from (order for order in orders if is_reconcilable(order, now))


def build_mismatch(
    order: PaymentOrderDocument, state: ProviderPaymentState
) -> PaymentMismatch | None:
    kind: PaymentMismatchKind | None = find_mismatch(order, state)
    if kind is None:
        return None

    return PaymentMismatch(
        payment_order_id=order.id,
        business_id=order.business_id,
        provider=order.provider,
        recorded_status=order.status,
        provider_status=state.status,
        kind=kind,
    )
