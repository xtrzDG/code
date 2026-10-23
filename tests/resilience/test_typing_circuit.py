"""
A typing signal is best effort and often makes no call at all (no
credential, nothing to reply to), so it runs only while its provider's
circuit is closed and never reports a success: it cannot take the trial
call of a half-open circuit, close it, or clear a closed one's failures.
A typing call that does time out still counts against the circuit.
"""

from typing import cast

import pytest

from app.adapters.channels.circuit_breaking_channel_adapter import (
    CircuitBreakingChannelAdapter,
)
from app.contracts.channels import ChannelAdapterContract
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.resilience import CircuitState, OutboundProvider
from app.schemas.dto.channels.channel_webhooks import ChannelDeliveryTarget
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ProviderCircuitOpenError,
)
from app.schemas.typings.channels.strings import ProviderMessageId
from app.utilities.resilience.provider_circuits import provider_circuit
from tests.channels.testbed import ChannelsTestbed
from tests.resilience.test_circuit_breaker import Ticks
from tests.resilience.test_provider_guards import TARGET

META = provider_circuit(OutboundProvider.META)
FAILURES_TO_OPEN: int = 5
OPEN_SECONDS: int = 30


class TimingOutTyping:
    """A channel whose typing call times out."""

    def __init__(self) -> None:
        self.calls: int = 0

    def signal_typing(
        self, target: ChannelDeliveryTarget, replying_to: ProviderMessageId | None
    ) -> None:
        del target, replying_to
        self.calls += 1
        raise ExternalServiceError("Meta timed out.")


def whatsapp(breaker: CircuitBreakerFacilitator) -> CircuitBreakingChannelAdapter:
    return CircuitBreakingChannelAdapter(
        ChannelsTestbed().whatsapp_adapter, breaker, META
    )


def test_a_typing_signal_without_a_call_leaves_a_half_open_circuit_half_open() -> None:
    ticks = Ticks()
    breaker = CircuitBreakerFacilitator(ticks.clock())
    for _ in range(FAILURES_TO_OPEN):
        breaker.record_failure(META)
    ticks.advance(OPEN_SECONDS)

    # Nothing to reply to: WhatsApp's typing makes no call.
    with pytest.raises(ProviderCircuitOpenError):
        whatsapp(breaker).signal_typing(TARGET, None)

    assert breaker.state(META) is not CircuitState.CLOSED
    # The trial call is still free for a real send.
    assert breaker.allows_call(META) is True


def test_a_typing_signal_without_a_call_keeps_a_closed_circuits_failures() -> None:
    breaker = CircuitBreakerFacilitator(Ticks().clock())
    for _ in range(FAILURES_TO_OPEN - 1):
        breaker.record_failure(META)

    whatsapp(breaker).signal_typing(TARGET, None)
    breaker.record_failure(META)

    assert breaker.state(META) is CircuitState.OPEN


def test_a_typing_call_that_times_out_counts_against_the_circuit() -> None:
    breaker = CircuitBreakerFacilitator(Ticks().clock())
    channel = TimingOutTyping()
    typing = CircuitBreakingChannelAdapter(
        cast(ChannelAdapterContract, channel), breaker, META
    )

    for _ in range(FAILURES_TO_OPEN):
        with pytest.raises(ExternalServiceError):
            typing.signal_typing(TARGET, ProviderMessageId("wamid.in"))
    with pytest.raises(ProviderCircuitOpenError):
        typing.signal_typing(TARGET, ProviderMessageId("wamid.in"))

    assert channel.calls == FAILURES_TO_OPEN
    assert breaker.state(META) is CircuitState.OPEN
