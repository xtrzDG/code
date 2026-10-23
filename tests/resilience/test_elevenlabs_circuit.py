"""
The voice platform's API behind its own circuit breaker (W20's breakers,
`provider:elevenlabs`): an outage opens it, an open circuit refuses at once
without a network call and is counted as a failure for voice_health, and
a trial call after the wait closes it again.
"""

import pytest

from app.adapters.telephony.guarded_elevenlabs_phone_numbers_client import (
    GuardedElevenLabsPhoneNumbersClient,
)
from app.adapters.voice.guarded_elevenlabs_client import GuardedElevenLabsClient
from app.contracts.telephony_clients import ElevenLabsPhoneNumbersClientContract
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.constants.resilience import CircuitState, OutboundProvider
from app.schemas.dto.phone_numbers.provisioning import VoicePlatformImport
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ProviderCircuitOpenError,
    ProviderRejectedMessageError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.messaging.constrained_strings import TwilioAccountSid
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.schemas.typings.telephony.constrained_strings import (
    PhoneNumberLabel,
    RentedLineNumber,
)
from app.schemas.typings.telephony.strings import VoicePlatformPhoneNumberId
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


class RecordedNumbers(ElevenLabsPhoneNumbersClientContract):
    """ElevenLabs' phone numbers that time out until told otherwise."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.is_down: bool = True

    def import_twilio_number(
        self,
        request: VoicePlatformImport,
        account_sid: TwilioAccountSid,
        auth_token: PlatformSecret,
    ) -> VoicePlatformPhoneNumberId:
        del account_sid, auth_token
        return VoicePlatformPhoneNumberId(self._call(f"import {request.phone_number}"))

    def assign_agent(
        self,
        phone_number_id: VoicePlatformPhoneNumberId,
        agent_id: VoiceAgentId | None,
    ) -> None:
        self._call(f"assign {phone_number_id} {agent_id}")

    def delete_number(self, phone_number_id: VoicePlatformPhoneNumberId) -> None:
        self._call(f"delete {phone_number_id}")

    def _call(self, call: str) -> str:
        self.calls.append(call)
        if self.is_down:
            raise ExternalServiceError("ElevenLabs phone-numbers request timed out.")
        return "phnum_1"


def test_elevenlabs_numbers_share_the_voice_platform_s_circuit() -> None:
    ticks = Ticks()
    breaker = CircuitBreakerFacilitator(ticks.clock())
    inner = RecordedNumbers()
    numbers = GuardedElevenLabsPhoneNumbersClient(inner, breaker, ELEVENLABS)
    number = VoicePlatformPhoneNumberId("phnum_1")

    for _ in range(5):
        with pytest.raises(ExternalServiceError):
            numbers.assign_agent(number, AGENT)
    with pytest.raises(ProviderCircuitOpenError):
        numbers.delete_number(number)
    with pytest.raises(ProviderCircuitOpenError):
        numbers.import_twilio_number(
            VoicePlatformImport(
                phone_number=RentedLineNumber("+15125550142"),
                label=PhoneNumberLabel("Austin Coffee Lab"),
            ),
            TwilioAccountSid("AC" + "0" * 32),
            PlatformSecret("test-token-0000"),
        )

    assert len(inner.calls) == 5
    assert breaker.state(ELEVENLABS) is CircuitState.OPEN
    ticks.advance(31)
    inner.is_down = False
    numbers.delete_number(number)
    assert breaker.state(ELEVENLABS) is CircuitState.CLOSED
