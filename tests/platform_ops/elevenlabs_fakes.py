"""An ElevenLabs API client whose calls succeed or fail by script."""

from app.contracts.channel_clients import ElevenLabsApiClientContract, JsonObject
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.call_recordings import RecordingAudio
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.channels.strings import VoicePlatformToolId
from app.schemas.typings.conversations.strings import ProviderCallId


class ScriptedElevenLabsClient(ElevenLabsApiClientContract):
    """Each call takes the next outcome: None succeeds, an error is raised."""

    def __init__(self, outcomes: list[ApplicationError | None]) -> None:
        self._outcomes: list[ApplicationError | None] = list(outcomes)

    def _next(self) -> None:
        outcome: ApplicationError | None = self._outcomes.pop(0)
        if outcome is not None:
            raise outcome

    def create_agent(self, agent_config: JsonObject) -> VoiceAgentId:
        self._next()
        return VoiceAgentId("agent_1")

    def get_agent_tool_ids(
        self, agent_id: VoiceAgentId
    ) -> list[VoicePlatformToolId] | None:
        self._next()
        return []

    def update_agent(self, agent_id: VoiceAgentId, agent_config: JsonObject) -> None:
        self._next()

    def delete_agent(self, agent_id: VoiceAgentId) -> None:
        self._next()

    def create_tool(self, tool_config: JsonObject) -> VoicePlatformToolId:
        self._next()
        return VoicePlatformToolId("tool_1")

    def get_tool_name(self, tool_id: VoicePlatformToolId) -> AssistantToolName | None:
        self._next()
        return None

    def update_tool(
        self, tool_id: VoicePlatformToolId, tool_config: JsonObject
    ) -> None:
        self._next()

    def delete_tool(self, tool_id: VoicePlatformToolId) -> None:
        self._next()

    def get_conversation_audio(
        self, conversation_id: ProviderCallId
    ) -> RecordingAudio | None:
        self._next()
        return None

    def delete_conversation(self, conversation_id: ProviderCallId) -> None:
        self._next()
