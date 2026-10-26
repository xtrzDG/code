"""
The real ElevenLabs clients behind provider:elevenlabs: a refusal the
platform answered (a 4xx such as 422 for a voice it does not offer, or a
429 asking to slow down) leaves the circuit closed, so one business's agent
setting cannot cut every other business off the voice platform; a 5xx or a
408 counts as an outage and opens it.
"""

import httpx
import pytest

from app.adapters.telephony.guarded_elevenlabs_phone_numbers_client import (
    GuardedElevenLabsPhoneNumbersClient,
)
from app.adapters.voice.guarded_elevenlabs_client import GuardedElevenLabsClient
from app.clients.elevenlabs.elevenlabs_client import ElevenLabsClient
from app.clients.elevenlabs.elevenlabs_phone_numbers_client import (
    ElevenLabsPhoneNumbersClient,
)
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.resilience import CircuitState, OutboundProvider
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ProviderCircuitOpenError,
    ProviderRateLimitedError,
    ProviderRejectedMessageError,
)
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.schemas.typings.telephony.strings import VoicePlatformPhoneNumberId
from app.utilities.resilience.provider_circuits import provider_circuit
from tests.platform_ops.ops_world import OpsWorld
from tests.resilience.test_circuit_breaker import Ticks

ELEVENLABS: CircuitName = provider_circuit(OutboundProvider.ELEVENLABS)
BASE_URL: PublicBaseUrl = PublicBaseUrl("https://api.eu.residency.elevenlabs.io")
API_KEY: PlatformSecret = PlatformSecret("test-token-0000")
AGENT: VoiceAgentId = VoiceAgentId("agent_1")
CALLS_TO_OPEN: int = 5


class Platform:
    """An ElevenLabs answering every request with one scripted status."""

    def __init__(self, status_code: int, headers: dict[str, str] | None = None) -> None:
        self.status_code: int = status_code
        self.headers: dict[str, str] = headers or {}
        self.requests: list[httpx.Request] = []
        self.ticks = Ticks()
        self.breaker = CircuitBreakerFacilitator(self.ticks.clock())
        transport = httpx.MockTransport(self._answer)
        self.client = GuardedElevenLabsClient(
            ElevenLabsClient(API_KEY, BASE_URL, transport),
            OpsWorld().signals,
            self.breaker,
            ELEVENLABS,
        )
        self.numbers = GuardedElevenLabsPhoneNumbersClient(
            ElevenLabsPhoneNumbersClient(API_KEY, BASE_URL, transport),
            self.breaker,
            ELEVENLABS,
        )

    def _answer(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(
            self.status_code,
            headers=self.headers,
            json={"detail": {"message": "Voice not available in this region."}},
        )


@pytest.mark.parametrize("status_code", [400, 401, 403, 409, 422])
def test_a_refusal_the_platform_answered_leaves_the_circuit_closed(
    status_code: int,
) -> None:
    platform = Platform(status_code)

    for _ in range(CALLS_TO_OPEN + 1):
        with pytest.raises(ProviderRejectedMessageError, match="Voice not available"):
            platform.client.update_agent(AGENT, {"name": "Agent"})

    assert platform.breaker.state(ELEVENLABS) is CircuitState.CLOSED
    with pytest.raises(ProviderRejectedMessageError):
        platform.client.delete_conversation(ProviderCallId("conv_1"))
    assert len(platform.requests) == CALLS_TO_OPEN + 2


def test_a_rate_limit_is_a_pause_not_an_outage() -> None:
    platform = Platform(429, {"Retry-After": "7"})

    for _ in range(CALLS_TO_OPEN + 1):
        with pytest.raises(ProviderRateLimitedError) as raised:
            platform.client.update_agent(AGENT, {"name": "Agent"})
        assert raised.value.retry_after_seconds == RetryAfterSeconds(7)

    assert platform.breaker.state(ELEVENLABS) is CircuitState.CLOSED


def test_a_refused_number_import_leaves_the_circuit_closed() -> None:
    platform = Platform(422)

    for _ in range(CALLS_TO_OPEN + 1):
        with pytest.raises(ProviderRejectedMessageError):
            platform.numbers.assign_agent(VoicePlatformPhoneNumberId("phnum_1"), AGENT)

    assert platform.breaker.state(ELEVENLABS) is CircuitState.CLOSED


@pytest.mark.parametrize("status_code", [408, 500, 503])
def test_a_platform_failure_opens_the_circuit(status_code: int) -> None:
    platform = Platform(status_code)

    for _ in range(CALLS_TO_OPEN):
        with pytest.raises(ExternalServiceError) as raised:
            platform.client.update_agent(AGENT, {"name": "Agent"})
        assert not isinstance(raised.value, ProviderRejectedMessageError)

    assert platform.breaker.state(ELEVENLABS) is CircuitState.OPEN
    with pytest.raises(ProviderCircuitOpenError):
        platform.client.delete_conversation(ProviderCallId("conv_1"))
    assert len(platform.requests) == CALLS_TO_OPEN
