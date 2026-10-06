"""
A small world for the idempotency keys: the repository over an in-memory
collection, the three use cases on a movable clock, and operators that run
them the way the container's chains do.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.operator_contract import OperatorContract
from app.contracts.use_case_contract import UseCaseContract
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.idempotency_key_repository import IdempotencyKeyRepository
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.idempotency_keys import IdempotencyKeyDocument
from app.schemas.dto.idempotency import (
    IdempotencyClaim,
    IdempotencyClaimDecision,
    IdempotentRequestOutcome,
)
from app.schemas.typings.idempotency.constrained_strings import (
    IdempotencyKey,
    IdempotencyRequestFingerprint,
    IdempotentOperation,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.idempotency.claim_idempotency_key_use_case import (
    ClaimIdempotencyKeyUseCase,
)
from app.use_cases.idempotency.finish_idempotent_request_use_case import (
    FinishIdempotentRequestUseCase,
)
from app.use_cases.idempotency.purge_idempotency_keys_use_case import (
    PurgeIdempotencyKeysUseCase,
)
from tests.e2e.edge_fakes import MovableClock

START: datetime = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)
OWNER: UserId = UserId("user_00000000-0000-4000-8000-000000000001")
OTHER_OWNER: UserId = UserId("user_00000000-0000-4000-8000-000000000002")
BOOKINGS: IdempotentOperation = IdempotentOperation(
    "POST /v1/businesses/{business_id}/bookings"
)
FIRST_BODY: IdempotencyRequestFingerprint = IdempotencyRequestFingerprint("a1" * 32)
OTHER_BODY: IdempotencyRequestFingerprint = IdempotencyRequestFingerprint("b2" * 32)
KEY: IdempotencyKey = IdempotencyKey("4b0e2a5c-7d1f-4e8a-9c3b-1f2e3d4c5b6a")


class RunUseCase[Input, Output](OperatorContract[Input, Output]):
    """An operator that runs its use case, like the container's chains."""

    def __init__(self, use_case: UseCaseContract[Input, Output]) -> None:
        self.use_case: UseCaseContract[Input, Output] = use_case
        self.calls: int = 0

    def operate(self, input_data: Input) -> Output:
        self.calls += 1
        return self.use_case.run(input_data)


@dataclass
class IdempotencyWorld:
    clock: MovableClock = field(default_factory=lambda: MovableClock(START))
    collection: InMemoryDocumentCollectionAdapter[IdempotencyKeyDocument] = field(
        default_factory=lambda: InMemoryDocumentCollectionAdapter(
            IdempotencyKeyDocument
        )
    )
    audit_collection: InMemoryDocumentCollectionAdapter[AuditLogEntryDocument] = field(
        default_factory=lambda: InMemoryDocumentCollectionAdapter(AuditLogEntryDocument)
    )

    @property
    def repo(self) -> IdempotencyKeyRepository:
        return IdempotencyKeyRepository(self.collection)

    @property
    def audit_log(self) -> AuditLogRepository:
        return AuditLogRepository(self.audit_collection)

    def claim_use_case(self) -> ClaimIdempotencyKeyUseCase:
        return ClaimIdempotencyKeyUseCase(self.repo, self.clock.wall_clock)

    def finish_use_case(self) -> FinishIdempotentRequestUseCase:
        return FinishIdempotentRequestUseCase(self.repo, self.clock.wall_clock)

    def purge_use_case(self) -> PurgeIdempotencyKeysUseCase:
        return PurgeIdempotencyKeysUseCase(
            self.repo, self.audit_log, self.clock.wall_clock
        )

    def claim_operator(
        self,
    ) -> RunUseCase[IdempotencyClaim, IdempotencyClaimDecision]:
        return RunUseCase(self.claim_use_case())

    def finish_operator(self) -> RunUseCase[IdempotentRequestOutcome, None]:
        return RunUseCase(self.finish_use_case())

    def records(self) -> list[IdempotencyKeyDocument]:
        return self.collection.list_all()


def claim_of(
    fingerprint: IdempotencyRequestFingerprint = FIRST_BODY,
    user_id: UserId = OWNER,
    operation: IdempotentOperation = BOOKINGS,
    key: IdempotencyKey = KEY,
) -> IdempotencyClaim:
    return IdempotencyClaim(
        user_id=user_id, key=key, operation=operation, fingerprint=fingerprint
    )
