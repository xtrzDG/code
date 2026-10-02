import json

from app.adapters.llm.llm_payloads import (
    build_tool_results_payload,
    build_user_text_payload,
)
from app.contracts.llm import LlmAdapterContract
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText

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
    """

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        return build_user_text_payload(text)

    def build_tool_results_turn(
        self,
        results: list[LlmToolResult],
    ) -> LlmProviderPayload:
        return build_tool_results_payload(results)

    def complete(self, request: LlmRequest) -> LlmResponse:
        del request
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
