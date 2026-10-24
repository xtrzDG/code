"""
Circuit breakers in front of external dependencies (language models, the
providers the platform sends through) and the outbound lane's bulkheads.
"""

from contextlib import AbstractContextManager
from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.constants.resilience import CircuitState, OutboundProvider
from app.schemas.dto.resilience import CircuitSnapshot
from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds
from app.schemas.typings.resilience.booleans import IsProviderSlotTaken
from app.schemas.typings.resilience.constrained_strings import CircuitName


class CircuitBreakerContract(FacilitatorContract, Protocol):
    """
    One breaker per circuit (a provider and its model, or a provider the
    platform sends through), shared by every thread of the process. A
    caller asks before each call and reports how it went; an open circuit
    is skipped at once instead of waited on.
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

    def seconds_until_trial(self, circuit: CircuitName) -> RetryAfterSeconds | None:
        """
        How long an open circuit still refuses calls (at least a second);
        None when it is closed or already lets its trial through.
        """
        raise NotImplementedError

    def snapshot(self) -> list[CircuitSnapshot]:
        """Every circuit this process knows, by name (the worker's pulse)."""
        raise NotImplementedError


class OutboundBulkheadContract(FacilitatorContract, Protocol):
    """
    Each provider's share of a worker's outbound threads: a send holds one
    slot of its provider while it talks to it, and a provider never holds
    more than its slots, so its brownout leaves the other threads to the
    other providers.
    """

    def reserve(
        self, provider: OutboundProvider
    ) -> AbstractContextManager[IsProviderSlotTaken]:
        """
        A slot of the provider for the block, never waited for: True when
        one was free (it is given back after the block), False when the
        provider's slots are all in use (send later).
        """
        raise NotImplementedError
