"""
The voice platform's API behind its own circuit breaker (W20's breakers,
`provider:elevenlabs`): an outage opens it, an open circuit refuses at once
without a network call and is counted as a failure for voice_health, and
a trial call after the wait closes it again.
"""

import pytest

from app.adapters.voice.guarded_elevenlabs_client import GuardedElevenLabsClient
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.constants.resilience import CircuitState, OutboundProvider
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ProviderCircuitOpenError,
    ProviderRejectedMessageError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.schemas.typings.voice.constrained_strings import VoiceCheckTestId
from app.utilities.resilience.provider_circuits import provider_circuit
from tests.platform_ops.elevenlabs_fakes import ScriptedElevenLabsClient
from tests.platform_ops.ops_world import OpsWorld
from tests.resilience.test_circuit_breaker import Ticks

ELEVENLABS: CircuitName = provider_circuit(OutboundProvider.ELEVENLABS)
AGENT: VoiceAgentId = VoiceAgentId("agent_1")


class Guarded:
    """The guarded client over a scripted one, its breaker and its signals."""

    def __init__(self, outcomes: list[ApplicationError | None]) -> None:
        self.ticks = Ticks()
        self.world = OpsWorld()
        self.inner = ScriptedElevenLabsClient(outcomes)
        self.breaker = CircuitBreakerFacilitator(self.ticks.clock())
        self.client = GuardedElevenLabsClient(
            self.inner, self.world.signals, self.breaker, ELEVENLABS
        )

    def signal(self, signal: PlatformSignal) -> int:
        now = self.world.clock.wall_clock.now_unix()
        return int(self.world.signals.read(signal, now).current)


def outage(guarded: Guarded, times: int) -> None:
    for _ in range(times):
        with pytest.raises(ExternalServiceError):
            guarded.client.delete_agent(AGENT)


def test_an_outage_opens_the_circuit_and_refusals_make_no_call() -> None:
    guarded = Guarded([ExternalServiceError("ElevenLabs timed out.")] * 5 + [None])

    outage(guarded, 5)

    assert guarded.breaker.state(ELEVENLABS) is CircuitState.OPEN
    with pytest.raises(ProviderCircuitOpenError):
        guarded.client.get_agent_tool_ids(AGENT)
    # The scripted client was not asked: its last outcome is still there.
    assert guarded.inner.get_agent_tool_ids(AGENT) == []
    # Refused calls count as failures of the voice platform for voice_health.
    assert guarded.signal(PlatformSignal.VOICE_API_CALL) == 6
    assert guarded.signal(PlatformSignal.VOICE_API_ERROR) == 6


def test_a_trial_after_the_wait_closes_it() -> None:
    guarded = Guarded([ExternalServiceError("ElevenLabs said 503.")] * 5 + [None])
    outage(guarded, 5)

    guarded.ticks.advance(31)
    guarded.client.delete_agent(AGENT)

    assert guarded.breaker.state(ELEVENLABS) is CircuitState.CLOSED


def test_a_refusal_the_platform_answered_is_no_outage() -> None:
    guarded = Guarded([ProviderRejectedMessageError("Refused.")] * 6)

    for _ in range(6):
        with pytest.raises(ProviderRejectedMessageError):
            guarded.client.delete_test(VoiceCheckTestId("test_1"))

    assert guarded.breaker.state(ELEVENLABS) is CircuitState.CLOSED
    assert guarded.signal(PlatformSignal.VOICE_API_ERROR) == 6


def test_the_voice_checks_go_through_the_circuit_too() -> None:
    guarded = Guarded([ExternalServiceError("ElevenLabs timed out.")] * 5)
    for _ in range(5):
        with pytest.raises(ExternalServiceError):
            guarded.client.run_tests(AGENT, [], None)

    assert guarded.breaker.state(ELEVENLABS) is CircuitState.OPEN
