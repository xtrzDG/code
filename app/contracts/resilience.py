"""Circuit breakers in front of external dependencies (language models)."""

from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.constants.resilience import CircuitState
from app.schemas.typings.resilience.constrained_strings import CircuitName


class CircuitBreakerContract(FacilitatorContract, Protocol):
    """
    One breaker per circuit (a provider and its model), shared by every
    thread of the process. A caller asks before each call and reports how
    it went; an open circuit is skipped at once instead of waited on.
    """

    def allows_call(self, circuit: CircuitName) -> bool:
        """
        True when the call may go ahead: the circuit is closed, or it has
        been open long enough and this call is its one trial.
        """
        raise NotImplementedError

    def record_success(self, circuit: CircuitName) -> None:
        raise NotImplementedError

    def record_failure(self, circuit: CircuitName) -> None:
        raise NotImplementedError

    def state(self, circuit: CircuitName) -> CircuitState:
        raise NotImplementedError
