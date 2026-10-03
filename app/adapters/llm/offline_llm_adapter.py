import json
import time
from collections.abc import Callable

from app.adapters.llm.llm_payloads import (
    build_tool_results_payload,
    build_user_text_payload,
)
from app.contracts.llm import LlmAdapterContract
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.typings.assistants.constrained_integers import (
    ScriptedLlmLatencyMilliseconds,
)
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText

# Without SCRIPTED_LLM_LATENCY_MS the scripted model answers at once.
NO_LATENCY: ScriptedLlmLatencyMilliseconds = ScriptedLlmLatencyMilliseconds(0)
# What the staging assistant answers to everything.
OFFLINE_REPLY: MessageText = MessageText(
    "Thank you for your message! This is the test assistant of a staging "
    "server: its answers are scripted, no language model reads your message."
)


class OfflineLlmAdapter(LlmAdapterContract):
    """
    The model of `LLM_PROVIDER=scripted` (model id "scripted"): a staging
    deployment, or a local run without provider keys, answers every turn
    with `OFFLINE_REPLY`, without tool calls, network or cost.

    Conversations, the widget, notifications and the post-deploy smoke test
    (scripts/smoke.sh) run end to end on it. It measures nothing about
    answer quality: autotest judges get the same sentence, so their checks
    fail on such a deployment. Unlike the tests' `ScriptedLlmAdapter` it
    keeps no requests, so a long-running process does not grow.

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

    def build_tool_results_turn(
        self,
        results: list[LlmToolResult],
    ) -> LlmProviderPayload:
        return build_tool_results_payload(results)

    def complete(self, request: LlmRequest) -> LlmResponse:
        del request
        if self._latency_seconds > 0:
            self._wait(self._latency_seconds)

        return LlmResponse(
            stop_reason=LlmStopReason.END_TURN,
            text=OFFLINE_REPLY,
            assistant_turn_payload=LlmProviderPayload(
                json.dumps(
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": str(OFFLINE_REPLY)}],
                    },
                    ensure_ascii=False,
                )
            ),
        )
