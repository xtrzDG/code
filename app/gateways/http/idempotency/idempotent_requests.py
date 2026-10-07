"""
What the idempotency dependency and the response recorder share about one
request: the claim it holds, and the replay of a stored answer.
"""

from collections.abc import Callable
from dataclasses import dataclass

from starlette.types import Scope

from app.schemas.dto.idempotency import IdempotentRequestOutcome, StoredResponse
from app.schemas.typings.idempotency.prefixed_id import (
    IdempotencyClaimId,
    IdempotencyRecordId,
)

IDEMPOTENCY_KEY_HEADER: str = "Idempotency-Key"
IDEMPOTENT_REPLAY_HEADER: str = "Idempotent-Replayed"
# Where the recorder leaves its slot in the request's ASGI scope.
SLOT_SCOPE_KEY: str = "workshop.idempotency"

type FinishIdempotentRequest = Callable[[IdempotentRequestOutcome], None]


@dataclass(frozen=True)
class PendingIdempotentRequest:
    """A request that holds its key: how to keep its answer or free the key."""

    record_id: IdempotencyRecordId
    claim_id: IdempotencyClaimId
    finish: FinishIdempotentRequest

    def outcome(self, response: StoredResponse | None) -> IdempotentRequestOutcome:
        return IdempotentRequestOutcome(
            record_id=self.record_id, claim_id=self.claim_id, response=response
        )


@dataclass
class IdempotencySlot:
    """Per request: filled by the dependency when the request claimed a key."""

    pending: PendingIdempotentRequest | None = None


def slot_of(scope: Scope) -> IdempotencySlot | None:
    slot: object = scope.get(SLOT_SCOPE_KEY)
    return slot if isinstance(slot, IdempotencySlot) else None


class IdempotentReplay(Exception):  # noqa: N818 - control flow, not an error
    """Raised by the dependency: answer with the stored response instead."""

    def __init__(self, response: StoredResponse) -> None:
        super().__init__("Replaying the stored answer of an idempotent request.")
        self.response: StoredResponse = response
