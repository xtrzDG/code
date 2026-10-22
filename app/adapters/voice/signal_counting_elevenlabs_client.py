"""Every call of the ElevenLabs API counted for the voice_health alert."""

from collections.abc import Callable

from app.contracts.channel_clients import ElevenLabsApiClientContract, JsonObject
from app.contracts.monitoring import SignalCounterAdapterContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.dto.call_recordings import RecordingAudio
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.channels.strings import VoicePlatformToolId
from app.schemas.typings.conversations.strings import ProviderCallId


class SignalCountingElevenLabsClient(ElevenLabsApiClientContract):
    """
    Decorator that counts every call of the voice platform's API, and every
    call the platform failed (an outage, a timeout, a 5xx: ExternalService
    Error), in the shared platform signals (`voice_api_call`,
    `voice_api_error`): the voice_health alert reads them. Otherwise it
    behaves like the wrapped client; counting never fails a call.
    """

    def __init__(
        self,
        inner_client: ElevenLabsApiClientContract,
        signal_counter: SignalCounterAdapterContract,
    ) -> None:
        self._inner: ElevenLabsApiClientContract = inner_client
        self._signal_counter: SignalCounterAdapterContract = signal_counter

    def _counted[Result](self, call: Callable[[], Result]) -> Result:
        self._signal_counter.count(PlatformSignal.VOICE_API_CALL)
        try:
            return call()
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
