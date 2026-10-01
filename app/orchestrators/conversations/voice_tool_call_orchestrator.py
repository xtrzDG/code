import uuid

from app.contracts.conversation_flow import VoiceToolCallOrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.assistant_tools import (
    AssistantToolContext,
    AssistantToolInvocation,
    AssistantToolOutcome,
)
from app.schemas.dto.conversation_engine import VoiceToolCallRecord
from app.schemas.dto.conversations import (
    LlmToolCall,
    VoiceToolCallRequest,
    VoiceToolCallResult,
)
from app.schemas.typings.conversations.strings import LlmToolCallId

VOICE_CALL_ID_PREFIX: str = "voice_"


class VoiceToolCallOrchestrator(VoiceToolCallOrchestratorContract):
    """
    Run one voice-agent tool call with the same tools and the same
    server-side checks as the chat (concept section 7): find or start the
    call's conversation, execute the tool, keep the call in the feed. No
    language model is involved, so the answer comes back well within the
    one-second target.
    """

    def __init__(
        self,
        open_voice_conversation: UseCaseContract[
            VoiceToolCallRequest, AssistantToolContext
        ],
        run_assistant_tool: UseCaseContract[
            AssistantToolInvocation, AssistantToolOutcome
        ],
        record_voice_tool_call: UseCaseContract[
            VoiceToolCallRecord, VoiceToolCallResult
        ],
    ) -> None:
        self._open_voice_conversation: UseCaseContract[
            VoiceToolCallRequest, AssistantToolContext
        ] = open_voice_conversation
        self._run_assistant_tool: UseCaseContract[
            AssistantToolInvocation, AssistantToolOutcome
        ] = run_assistant_tool
        self._record_voice_tool_call: UseCaseContract[
            VoiceToolCallRecord, VoiceToolCallResult
        ] = record_voice_tool_call

    def execute(self, input_data: VoiceToolCallRequest) -> VoiceToolCallResult:
        context: AssistantToolContext = self._open_voice_conversation.run(input_data)
        call = LlmToolCall(
            call_id=LlmToolCallId(f"{VOICE_CALL_ID_PREFIX}{uuid.uuid4().hex}"),
            tool_name=input_data.tool_name,
            input_json=input_data.input_json,
        )
        outcome: AssistantToolOutcome = self._run_assistant_tool.run(
            AssistantToolInvocation(context=context, call=call)
        )
        return self._record_voice_tool_call.run(
            VoiceToolCallRecord(context=context, call=call, outcome=outcome)
        )
