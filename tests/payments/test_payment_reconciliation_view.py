"""
The admin's view of the latest payment reconciliation: each mismatch with
its client's name, the names read in one go (never one read per row).
"""

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.business_repositories import BusinessRepository
from app.repositories.platform_safety_repositories import (
    PaymentReconciliationRepository,
)
from app.schemas.constants.payment_reconciliation import PaymentMismatchKind
from app.schemas.constants.payments import PaymentProvider, PaymentStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payment_reconciliations import (
    PaymentMismatch,
    PaymentReconciliationDocument,
)
from app.schemas.dto.payment_reconciliation import PaymentReconciliationQuery
from app.schemas.typings.billing.constrained_integers import ReconciledOrderCount
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.billing.reconciliation.get_payment_reconciliation_use_case import (
    GetPaymentReconciliationUseCase,
)
from app.use_cases.shared.payment_reconciliation_days import reconciliation_day
from tests.payments.reconciliation_fakes import NOW
from tests.spend_guard.platform_pause_world import PauseWorld
from tests.storage.builders import COUNTRY_SAMPLES, build_business


class CountingBusinesses(BusinessRepository):
    """Counts the reads of businesses by id."""

    def __init__(self) -> None:
        super().__init__(InMemoryDocumentCollectionAdapter(BusinessDocument))
        self.reads: int = 0

    def get(self, business_id: BusinessId) -> BusinessDocument | None:
        self.reads += 1
        return super().get(business_id)

    def get_many(self, business_ids: list[BusinessId]) -> list[BusinessDocument]:
        self.reads += 1
        return super().get_many(business_ids)


def mismatch(business_id: BusinessId) -> PaymentMismatch:
    return PaymentMismatch(
        payment_order_id=PaymentOrderId(),
        business_id=business_id,
        provider=PaymentProvider.FLITT,
        recorded_status=PaymentStatus.CREATED,
        provider_status=PaymentStatus.APPROVED,
        kind=PaymentMismatchKind.PAID_AT_PROVIDER,
    )


def test_each_mismatch_names_its_client_from_one_read() -> None:
    world = PauseWorld()
    businesses = CountingBusinesses()
    client = build_business(COUNTRY_SAMPLES[0], UserId())
    businesses.save(client)
    gone = BusinessId()
    results = PaymentReconciliationRepository(
        InMemoryDocumentCollectionAdapter(PaymentReconciliationDocument)
    )
    results.save(
        PaymentReconciliationDocument(
            day=reconciliation_day(NOW),
            ran_at=NOW,
            checked_count=ReconciledOrderCount(3),
            unreadable_count=ReconciledOrderCount(0),
            mismatches=[mismatch(client.id), mismatch(gone), mismatch(client.id)],
            created_at=NOW,
            updated_at=NOW,
        )
    )
    businesses.reads = 0

    view = GetPaymentReconciliationUseCase(
        world.admins(), results, businesses, world.wall_clock()
    ).run(PaymentReconciliationQuery(user_id=world.billing))

    assert [m.business_name for m in view.mismatches] == [
        client.name,
        None,
        client.name,
    ]
    assert businesses.reads == 1
