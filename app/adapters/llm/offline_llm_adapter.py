import json
import time
import uuid
from collections.abc import Callable, Sequence

from app.adapters.llm.llm_payloads import (
    build_tool_results_payload,
    build_user_media_payload,
    build_user_text_payload,
)
from app.contracts.llm import LlmAdapterContract
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.dto.conversations import (
    LlmRequest,
    LlmResponse,
    LlmToolCall,
    LlmToolResult,
)
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.dto.media import LlmImageInput
from app.schemas.typings.assistants.constrained_integers import (
    ScriptedLlmLatencyMilliseconds,
)
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    LlmToolCallId,
    MessageText,
)
from app.utilities.llm_rehearsal.rehearsal_turns import play_rehearsal_turn

# Without SCRIPTED_LLM_LATENCY_MS the scripted model answers at once.
NO_LATENCY: ScriptedLlmLatencyMilliseconds = ScriptedLlmLatencyMilliseconds(0)
TOOL_CALL_ID_PREFIX: str = "toolu_rehearsal_"


class OfflineLlmAdapter(LlmAdapterContract):
    """
    The model of `LLM_PROVIDER=scripted` (model id "scripted"): a staging
    deployment, a local run without provider keys or the end-to-end
    suite. It plays a rehearsal instead of reading (see
    `app/utilities/llm_rehearsal/rehearsal_turns.py`): the automatic checks'
    AI customer and judge, and an assistant that answers in the customer's
    language that it is a test assistant, books the first free time when
    asked to book and passes the conversation to a colleague when asked
    for a person. So "Apply changes" goes live on such a server, without
    network or cost. It measures nothing about answer quality: its judge
    scores every answer 5, and only the checks of what the assistant did
    can fail. Unlike the tests' `ScriptedLlmAdapter` it keeps no requests,
    so a long-running process does not grow.

    Load tests (perf/k6) set SCRIPTED_LLM_LATENCY_MS: every answer then
    waits that long, as a real provider would, so a thread stays busy
    for the same time it does in production.
    """

    def __init__(
        self,
        latency_ms: ScriptedLlmLatencyMilliseconds = NO_LATENCY,
        wait: Callable[[float], None] = time.sleep,
    ) -> None:
        self._latency_seconds: float = int(latency_ms) / 1000
        self._wait: Callable[[float], None] = wait

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        return build_user_text_payload(text)

    def build_user_media_turn(
        self,
        text: MessageText,
        images: Sequence[LlmImageInput],
    ) -> LlmProviderPayload:
        return build_user_media_payload(text, images)

    def build_tool_results_turn(
        self,
        results: list[LlmToolResult],
    ) -> LlmProviderPayload:
        return build_tool_results_payload(results)

    def complete(self, request: LlmRequest) -> LlmResponse:
        if self._latency_seconds > 0:
            self._wait(self._latency_seconds)

        return build_response(play_rehearsal_turn(request))


def build_response(turn: ScriptedLlmTurn) -> LlmResponse:
    """The rehearsal's turn as a provider answer, in the canonical payload shape."""

    content: list[dict[str, object]] = []
    tool_calls: list[LlmToolCall] = []
    if turn.text is not None:
        content.append({"type": "text", "text": str(turn.text)})

    for scripted_call in turn.tool_calls:
        call_id = LlmToolCallId(f"{TOOL_CALL_ID_PREFIX}{uuid.uuid4().hex[:16]}")
        content.append(
            {
                "type": "tool_use",
                "id": str(call_id),
                "name": str(scripted_call.tool_name),
                "input": json.loads(scripted_call.input_json),
            }
        )
        tool_calls.append(
            LlmToolCall(
                call_id=call_id,
                tool_name=scripted_call.tool_name,
                input_json=scripted_call.input_json,
            )
        )

    return LlmResponse(
        stop_reason=LlmStopReason.TOOL_USE if tool_calls else LlmStopReason.END_TURN,
        text=turn.text,
        tool_calls=tool_calls,
        assistant_turn_payload=LlmProviderPayload(
            json.dumps({"role": "assistant", "content": content}, ensure_ascii=False)
        ),
    )
