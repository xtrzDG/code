from app.contracts.conversation_flow import VoiceToolCallOrchestratorContract
from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.conversations import VoiceToolCallRequest, VoiceToolCallResult
from app.schemas.dto.voice_webhooks import VoiceToolWebhookRequest


class VoiceToolWebhookOrchestrator(
    OrchestratorContract[VoiceToolWebhookRequest, VoiceToolCallResult]
):
    """
    A tool call of a business's voice agent (concept section 7: the agent's
    tools are our webhooks): authenticate the webhook and read the call,
    then run the tool with the same tools and checks the chat uses.
    """

    def __init__(
        self,
        authenticate_voice_tool_call: UseCaseContract[
            VoiceToolWebhookRequest,
            VoiceToolCallRequest,
        ],
        voice_tool_call: VoiceToolCallOrchestratorContract,
    ) -> None:
        self._authenticate_voice_tool_call: UseCaseContract[
            VoiceToolWebhookRequest,
            VoiceToolCallRequest,
        ] = authenticate_voice_tool_call
        self._voice_tool_call: VoiceToolCallOrchestratorContract = voice_tool_call

    def execute(self, input_data: VoiceToolWebhookRequest) -> VoiceToolCallResult:
        request: VoiceToolCallRequest = self._authenticate_voice_tool_call.run(
            input_data
        )
        return self._voice_tool_call.execute(request)
