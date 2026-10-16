from app.contracts.channel_clients import ElevenLabsApiClientContract, JsonObject
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.call_recordings import RecordingAudio
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.channels.strings import VoicePlatformToolId
from app.schemas.typings.conversations.strings import ProviderCallId

NOT_CONFIGURED_MESSAGE: str = "Voice is not configured: ELEVENLABS_API_KEY is missing."


class UnconfiguredElevenLabsClient(ElevenLabsApiClientContract):
    """
    Stand-in used while ELEVENLABS_API_KEY is not set.

    The application still starts (voice is optional per plan); every call
    fails with ExternalServiceError (HTTP 502), so publishing a voice
    version, playing or deleting a voice recording reports the missing key
    instead of pretending to succeed.
    """

    def create_agent(self, agent_config: JsonObject) -> VoiceAgentId:
        del agent_config
        raise ExternalServiceError(NOT_CONFIGURED_MESSAGE)

    def get_agent_tool_ids(
        self,
        agent_id: VoiceAgentId,
    ) -> list[VoicePlatformToolId] | None:
        del agent_id
        raise ExternalServiceError(NOT_CONFIGURED_MESSAGE)

    def update_agent(self, agent_id: VoiceAgentId, agent_config: JsonObject) -> None:
        del agent_id, agent_config
        raise ExternalServiceError(NOT_CONFIGURED_MESSAGE)

    def delete_agent(self, agent_id: VoiceAgentId) -> None:
        del agent_id
        raise ExternalServiceError(NOT_CONFIGURED_MESSAGE)

    def create_tool(self, tool_config: JsonObject) -> VoicePlatformToolId:
        del tool_config
        raise ExternalServiceError(NOT_CONFIGURED_MESSAGE)

    def get_tool_name(self, tool_id: VoicePlatformToolId) -> AssistantToolName | None:
        del tool_id
        raise ExternalServiceError(NOT_CONFIGURED_MESSAGE)

    def update_tool(
        self,
        tool_id: VoicePlatformToolId,
        tool_config: JsonObject,
    ) -> None:
        del tool_id, tool_config
        raise ExternalServiceError(NOT_CONFIGURED_MESSAGE)

    def delete_tool(self, tool_id: VoicePlatformToolId) -> None:
        del tool_id
        raise ExternalServiceError(NOT_CONFIGURED_MESSAGE)

    def get_conversation_audio(
        self,
        conversation_id: ProviderCallId,
    ) -> RecordingAudio | None:
        del conversation_id
        raise ExternalServiceError(NOT_CONFIGURED_MESSAGE)

    def delete_conversation(self, conversation_id: ProviderCallId) -> None:
        del conversation_id
        raise ExternalServiceError(NOT_CONFIGURED_MESSAGE)
