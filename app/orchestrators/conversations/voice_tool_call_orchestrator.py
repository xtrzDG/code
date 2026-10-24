import uuid

from app.contracts.conversation_flow import VoiceToolCallOrchestratorContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
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
from app.utilities.observability.log_context import bound_log_context

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
        storage_scope: StorageScopeContract,
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
        self._storage_scope: StorageScopeContract = storage_scope

    def execute(self, input_data: VoiceToolCallRequest) -> VoiceToolCallResult:
        # The business comes from the verified webhook; the tool sees only
        # its rows (row-level security on Postgres).
        with (
            bound_log_context(
                business_id=input_data.business_id, channel=ChannelKind.PHONE
            ),
            self._storage_scope.scoped_to_business(input_data.business_id),
        ):
            return self._run(input_data)

    def _run(self, input_data: VoiceToolCallRequest) -> VoiceToolCallResult:
        context: AssistantToolContext = self._open_voice_conversation.run(input_data)
        with bound_log_context(conversation_id=context.conversation_id):
            return self._run_tool(input_data, context)

    def _run_tool(
        self,
        input_data: VoiceToolCallRequest,
        context: AssistantToolContext,
    ) -> VoiceToolCallResult:
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
