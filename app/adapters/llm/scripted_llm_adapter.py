import json
import threading
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
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    LlmToolCallId,
    MessageText,
)

type ScriptedLlmResponder = Callable[[LlmRequest], ScriptedLlmTurn]


class ScriptedLlmAdapter(LlmAdapterContract):
    """
    Deterministic language model for tests and offline development.

    Every `complete` call asks the responder for the next turn. Requests are
    recorded in `requests` so tests can assert on prompts, tools, and the
    replayed transcript.
    """

    def __init__(self, responder: ScriptedLlmResponder) -> None:
        self._responder: ScriptedLlmResponder = responder
        self._lock: threading.Lock = threading.Lock()
        self._next_call_number: int = 1
        self.requests: list[LlmRequest] = []

    @classmethod
    def from_turns(cls, turns: list[ScriptedLlmTurn]) -> ScriptedLlmAdapter:
        """Answer with the given turns in order; fail when they run out."""

        remaining_turns: list[ScriptedLlmTurn] = list(turns)

        def respond_in_order(request: LlmRequest) -> ScriptedLlmTurn:
            del request
            if not remaining_turns:
                raise ExternalServiceError("Scripted language model ran out of turns.")

            return remaining_turns.pop(0)

        return cls(respond_in_order)

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
        with self._lock:
            self.requests.append(request)

        scripted_turn: ScriptedLlmTurn = self._responder(request)
        content: list[dict[str, object]] = []
        tool_calls: list[LlmToolCall] = []
        if scripted_turn.text is not None:
            content.append({"type": "text", "text": str(scripted_turn.text)})

        for scripted_call in scripted_turn.tool_calls:
            call_id = LlmToolCallId(self._allocate_call_id())
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
            stop_reason=(
                LlmStopReason.TOOL_USE if tool_calls else LlmStopReason.END_TURN
            ),
            text=scripted_turn.text,
            tool_calls=tool_calls,
            assistant_turn_payload=LlmProviderPayload(
                json.dumps(
                    {"role": "assistant", "content": content},
                    ensure_ascii=False,
                )
            ),
        )

    def _allocate_call_id(self) -> str:
        with self._lock:
            call_number: int = self._next_call_number
            self._next_call_number += 1

        return f"toolu_scripted_{call_number:04d}"
