"""
Every call of the ElevenLabs API counted for the voice_health alert and
made through the voice platform's circuit breaker.
"""

from collections.abc import Callable

from app.contracts.channel_clients import JsonObject
from app.contracts.monitoring import SignalCounterAdapterContract
from app.contracts.resilience import CircuitBreakerContract
from app.contracts.voice_check_clients import ElevenLabsPlatformClientContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.dto.call_recordings import RecordingAudio
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.channels.strings import VoicePlatformToolId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.schemas.typings.voice.constrained_strings import (
    VoiceCheckInvocationId,
    VoiceCheckTestId,
)
from app.utilities.resilience.circuit_calls import call_through_circuit


class GuardedElevenLabsClient(ElevenLabsPlatformClientContract):
    """
    Decorator of the voice platform's API client (agents and their tools,
    recordings, the deletion of calls, the voice checks):

    - every call goes through the platform's circuit breaker
      (`provider:elevenlabs`, W20): while it is open a call fails at once
      with ProviderCircuitOpenError and makes no network call, so an outage
      costs one refused call instead of a 20 s timeout each; timeouts and
      5xx count against the circuit, a refusal ElevenLabs answered does not;
    - every call is counted in the shared platform signals
      (`voice_api_call`), and every call that failed (an outage, a timeout,
      a 5xx, a circuit that refused it: ExternalServiceError) too
      (`voice_api_error`): the voice_health alert reads them. Counting never
      fails a call.

    Otherwise it behaves like the wrapped client.
    """

    def __init__(
        self,
        inner_client: ElevenLabsPlatformClientContract,
        signal_counter: SignalCounterAdapterContract,
        circuit_breaker: CircuitBreakerContract,
        circuit: CircuitName,
    ) -> None:
        self._inner: ElevenLabsPlatformClientContract = inner_client
        self._signal_counter: SignalCounterAdapterContract = signal_counter
        self._circuit_breaker: CircuitBreakerContract = circuit_breaker
        self._circuit: CircuitName = circuit

    def _counted[Result](self, call: Callable[[], Result]) -> Result:
        self._signal_counter.count(PlatformSignal.VOICE_API_CALL)
        try:
            return call_through_circuit(self._circuit_breaker, self._circuit, call)
        except ExternalServiceError:
            self._signal_counter.count(PlatformSignal.VOICE_API_ERROR)
            raise

    def create_agent(self, agent_config: JsonObject) -> VoiceAgentId:
        return self._counted(lambda: self._inner.create_agent(agent_config))

    def get_agent_tool_ids(
        self, agent_id: VoiceAgentId
    ) -> list[VoicePlatformToolId] | None:
        return self._counted(lambda: self._inner.get_agent_tool_ids(agent_id))

    def update_agent(self, agent_id: VoiceAgentId, agent_config: JsonObject) -> None:
        self._counted(lambda: self._inner.update_agent(agent_id, agent_config))

    def delete_agent(self, agent_id: VoiceAgentId) -> None:
        self._counted(lambda: self._inner.delete_agent(agent_id))

    def create_tool(self, tool_config: JsonObject) -> VoicePlatformToolId:
        return self._counted(lambda: self._inner.create_tool(tool_config))

    def get_tool_name(self, tool_id: VoicePlatformToolId) -> AssistantToolName | None:
        return self._counted(lambda: self._inner.get_tool_name(tool_id))

    def update_tool(
        self, tool_id: VoicePlatformToolId, tool_config: JsonObject
    ) -> None:
        self._counted(lambda: self._inner.update_tool(tool_id, tool_config))

    def delete_tool(self, tool_id: VoicePlatformToolId) -> None:
        self._counted(lambda: self._inner.delete_tool(tool_id))

    def get_conversation_audio(
        self, conversation_id: ProviderCallId
    ) -> RecordingAudio | None:
        return self._counted(
            lambda: self._inner.get_conversation_audio(conversation_id)
        )

    def delete_conversation(self, conversation_id: ProviderCallId) -> None:
        self._counted(lambda: self._inner.delete_conversation(conversation_id))

    def create_test(self, test_config: JsonObject) -> VoiceCheckTestId:
        return self._counted(lambda: self._inner.create_test(test_config))

    def run_tests(
        self,
        agent_id: VoiceAgentId,
        test_ids: list[VoiceCheckTestId],
        agent_config_override: JsonObject | None,
    ) -> VoiceCheckInvocationId:
        return self._counted(
            lambda: self._inner.run_tests(agent_id, test_ids, agent_config_override)
        )

    def get_test_invocation(
        self, invocation_id: VoiceCheckInvocationId
    ) -> JsonObject | None:
        return self._counted(lambda: self._inner.get_test_invocation(invocation_id))

    def delete_test(self, test_id: VoiceCheckTestId) -> None:
        self._counted(lambda: self._inner.delete_test(test_id))
