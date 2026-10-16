from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.idempotency_repositories import (
    IdempotencyKeyRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.idempotency import IdempotentRequestOutcome


class FinishIdempotentRequestUseCase(UseCaseContract[IdempotentRequestOutcome, None]):
    """
    Settle the key of a request that held it: a success stores its answer,
    which every retry with the key then gets for the rest of the key's day;
    a refusal or failure releases the key, so a retry runs again. Nothing
    changes when the request no longer holds the key (it outlived its lease
    and a retry took over).
    """

    def __init__(
        self,
        idempotency_key_repo: IdempotencyKeyRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._idempotency_key_repo: IdempotencyKeyRepoContract = idempotency_key_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: IdempotentRequestOutcome) -> None:
        now: Microseconds = self._wall_clock.now_unix()
        if input_data.response is None:
            self._idempotency_key_repo.release(
                input_data.record_id, input_data.claim_id, now
            )
            return

        self._idempotency_key_repo.complete(
            input_data.record_id, input_data.claim_id, input_data.response, now
        )
