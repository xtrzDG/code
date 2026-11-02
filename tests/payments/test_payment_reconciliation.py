"""
The daily payment reconciliation: recent checkout orders compared with
what Flitt or Stripe says now; the mismatches that move money are kept for
the `payment_mismatch` alert and the admin, and logged as structured
lines without card data. Nothing is changed.
"""

import logging

import pytest

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.business_repositories import BusinessRepository
from app.repositories.payment_repositories import PaymentOrderRepository
from app.repositories.platform_safety_repositories import (
    PaymentReconciliationRepository,
)
from app.schemas.constants.payment_reconciliation import PaymentMismatchKind
from app.schemas.constants.payments import (
    PaymentOrderPurpose,
    PaymentStatus,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payment_reconciliations import PaymentReconciliationDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.payment_reconciliation import ProviderPaymentState
from app.schemas.typings.billing.constrained_strings import ReconciliationDay
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.billing.payment_state_events import (
    PAYMENT_RECONCILIATION_MISMATCH,
)
from app.use_cases.billing.reconciliation import reconcile_payments_use_case
from app.use_cases.billing.reconciliation.payment_mismatch_rules import find_mismatch
from app.use_cases.billing.reconciliation.reconcile_payments_use_case import (
    ReconcilePaymentsUseCase,
)
from app.utilities.observability.log_formatting import read_line_fields
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.payments.reconciliation_fakes import NOW, FakeStatusReader, payment_order
from tests.spend_guard.platform_pause_world import PauseWorld
from tests.storage.builders import COUNTRY_SAMPLES
from tests.storage.builders import build_business as build_country_business


def build_business() -> BusinessDocument:
    return build_country_business(COUNTRY_SAMPLES[0], UserId())


APPROVED, DECLINED = PaymentStatus.APPROVED, PaymentStatus.DECLINED


def state(status: PaymentStatus, *, is_first: bool = True) -> ProviderPaymentState:
    return ProviderPaymentState(
        reference=PaymentProviderReference("ord_1"),
        status=status,
        is_first_payment=is_first,
    )


@pytest.mark.parametrize(
    ("recorded", "is_settled", "provider", "is_first", "expected"),
    [
        (PaymentStatus.CREATED, False, APPROVED, True, "paid_at_provider"),
        (PaymentStatus.PROCESSING, False, APPROVED, True, "paid_at_provider"),
        (APPROVED, True, APPROVED, True, None),
        # A later charge declined; the first payment was paid at both.
        (DECLINED, True, APPROVED, True, None),
        (APPROVED, True, DECLINED, True, "failed_at_provider"),
        (APPROVED, True, PaymentStatus.EXPIRED, True, "failed_at_provider"),
        (APPROVED, True, PaymentStatus.REVERSED, True, "reversed_at_provider"),
        (PaymentStatus.REVERSED, True, PaymentStatus.REVERSED, True, None),
        (PaymentStatus.CREATED, False, PaymentStatus.PROCESSING, True, None),
        (PaymentStatus.CREATED, False, PaymentStatus.EXPIRED, True, None),
        # Stripe's latest invoice: paid there, declined here.
        (DECLINED, True, APPROVED, False, "paid_at_provider"),
        (APPROVED, True, DECLINED, False, "failed_at_provider"),
    ],
)
def test_only_differences_that_move_money_are_mismatches(
    recorded: PaymentStatus,
    is_settled: bool,
    provider: PaymentStatus,
    is_first: bool,
    expected: str | None,
) -> None:
    order = payment_order(build_business().id, recorded, is_settled=is_settled)

    kind = find_mismatch(order, state(provider, is_first=is_first))

    assert (None if kind is None else kind.value) == expected


class ReconciliationWorld:
    def __init__(self) -> None:
        self.storage_scope = StorageScopeContext()
        self.businesses = BusinessRepository(
            InMemoryDocumentCollectionAdapter(BusinessDocument)
        )
        self.orders = PaymentOrderRepository(
            InMemoryDocumentCollectionAdapter(PaymentOrderDocument)
        )
        self.results = PaymentReconciliationRepository(
            InMemoryDocumentCollectionAdapter(PaymentReconciliationDocument)
        )
        self.business = build_business()
        self.businesses.save(self.business)

    def add(self, order: PaymentOrderDocument) -> PaymentOrderDocument:
        with self.storage_scope.scoped_to_business(order.business_id):
            self.orders.save(order)
        return order

    def run(self, reader: FakeStatusReader) -> PaymentReconciliationDocument:
        ReconcilePaymentsUseCase(
            self.businesses,
            self.orders,
            reader,
            self.results,
            self.storage_scope,
            PauseWorld().wall_clock(),
        ).run(JobTick(job_name=JobName("reconcile_payments"), scheduled_at=NOW))
        stored = self.results.get(ReconciliationDay("2026-11-02"))
        assert stored is not None
        return stored


def test_a_lost_notification_is_found_kept_and_logged_without_card_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    world = ReconciliationWorld()
    lost = world.add(payment_order(world.business.id, PaymentStatus.CREATED))
    paid = world.add(payment_order(world.business.id, APPROVED, is_settled=True))
    reader = FakeStatusReader({lost.id: APPROVED, paid.id: APPROVED})

    with caplog.at_level(logging.WARNING, logger="app.payments"):
        result = world.run(reader)

    assert int(result.checked_count) == 2 and int(result.unreadable_count) == 0
    (mismatch,) = result.mismatches
    assert mismatch.payment_order_id == lost.id
    assert mismatch.business_id == world.business.id
    assert mismatch.kind is PaymentMismatchKind.PAID_AT_PROVIDER
    assert mismatch.recorded_status is PaymentStatus.CREATED
    (line,) = [r for r in caplog.records if r.name == "app.payments"]
    fields: dict[str, object] = read_line_fields(line)
    assert fields["payment_event"] == PAYMENT_RECONCILIATION_MISMATCH
    assert fields["payment_order_id"] == str(lost.id)
    assert fields["provider_status"] == "approved"
    assert not {"masked_card", "card", "rectoken", "amount"} & set(fields)
    # Nothing changed on the order itself.
    with world.storage_scope.scoped_to_business(world.business.id):
        stored = world.orders.get(lost.id)
    assert stored is not None and stored.status is PaymentStatus.CREATED


def test_old_orders_and_card_setups_are_not_asked_about() -> None:
    world = ReconciliationWorld()
    old = world.add(payment_order(world.business.id, APPROVED, written_days_ago=8))
    setup = world.add(
        payment_order(
            world.business.id,
            PaymentStatus.CREATED,
            purpose=PaymentOrderPurpose.CARD_SETUP,
        )
    )
    reader = FakeStatusReader({old.id: DECLINED, setup.id: APPROVED})

    result = world.run(reader)

    assert reader.asked == []
    assert int(result.checked_count) == 0 and result.mismatches == []


def test_an_unreachable_provider_counts_as_unreadable_and_the_run_goes_on() -> None:
    world = ReconciliationWorld()
    down = world.add(payment_order(world.business.id, APPROVED, is_settled=True))
    unknown = world.add(payment_order(world.business.id, PaymentStatus.CREATED))
    failed = world.add(payment_order(world.business.id, APPROVED, is_settled=True))
    reader = FakeStatusReader(
        {unknown.id: None, failed.id: DECLINED}, unreachable=frozenset({down.id})
    )

    result = world.run(reader)

    assert int(result.unreadable_count) == 1
    assert int(result.checked_count) == 1
    assert [m.kind for m in result.mismatches] == [
        PaymentMismatchKind.FAILED_AT_PROVIDER
    ]


def test_a_run_asks_the_providers_at_most_its_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(reconcile_payments_use_case, "MAX_PROVIDER_READS", 2)
    world = ReconciliationWorld()
    orders = [
        world.add(payment_order(world.business.id, APPROVED, is_settled=True))
        for _ in range(4)
    ]
    reader = FakeStatusReader({order.id: APPROVED for order in orders})

    result = world.run(reader)

    assert len(reader.asked) == 2 and int(result.checked_count) == 2
