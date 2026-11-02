import logging
from collections.abc import Iterator

from typed_time_provider import Microseconds, WallClock

from app.contracts.billing import PaymentOrderRepoContract
from app.contracts.platform_safety import (
    PaymentReconciliationRepoContract,
    PaymentStatusReaderAdapterContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
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
from app.use_cases.shared.payment_reconciliation_days import (
    reconciliation_day,
)
from app.use_cases.shared.business_walk import walk_businesses

logger: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000
# Orders written to in the last week are compared: a payment whose
# notification was lost left its order as it was when the checkout opened.
RECONCILIATION_WINDOW_DAYS: int = 7
# The most provider calls one run makes (a busy week stays within an hour).
MAX_PROVIDER_READS: int = 2_000


class ReconcilePaymentsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    The `reconcile_payments` periodic job (daily, once across workers):
    every checkout order written to in the last RECONCILIATION_WINDOW_DAYS
    (the businesses walked in keyset batches, their orders by business) is
    compared with what Flitt or Stripe says about it now
    (`PaymentStatusReaderAdapterContract`, read-only calls). A mismatch
    that moves money (`find_mismatch`) is logged as a structured
    `payment_reconciliation_mismatch` line (ids and statuses, no card
    data) and kept in the day's result (`payment_reconciliations`), which
    the `payment_mismatch` platform alert and the admin's reconciliation
    view read. Nothing is changed: the platform admin settles a mismatch
    (docs/operations/runbooks/payment-mismatch.md).

    An order the provider cannot tell about now (it is down, it answers
    unreadably) counts as unreadable and the run goes on; at most
    MAX_PROVIDER_READS orders are asked about per run.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        payment_order_repo: PaymentOrderRepoContract,
        payment_status_reader: PaymentStatusReaderAdapterContract,
        reconciliation_repo: PaymentReconciliationRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._payment_order_repo: PaymentOrderRepoContract = payment_order_repo
        self._reader: PaymentStatusReaderAdapterContract = payment_status_reader
        self._reconciliation_repo: PaymentReconciliationRepoContract = (
            reconciliation_repo
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        now: Microseconds = self._wall_clock.now_unix()
        since = Microseconds(
            int(now) - RECONCILIATION_WINDOW_DAYS * MICROSECONDS_PER_DAY
        )
        checked: int = 0
        unreadable: int = 0
        mismatches: list[PaymentMismatch] = []
        for order in self._recent_orders(since):
            if checked + unreadable >= MAX_PROVIDER_READS:
                logger.warning(
                    "Payment reconciliation stopped after %d provider reads",
                    MAX_PROVIDER_READS,
                )
                break

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

    def _recent_orders(self, since: Microseconds) -> Iterator[PaymentOrderDocument]:
        """One business's orders at a time, in the walk's order."""

        for business in walk_businesses(self._business_repo):
            for order in self._payment_order_repo.list_by_business(business.id):
                if is_reconcilable(order, since):
                    yield order


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
