"""Anthropic Messages API turn shapes shared by the real and scripted adapters.

Payloads are JSON objects `{"role": ..., "content": [...]}` stored verbatim
and replayed in order, so the transcript stays append-only.
"""

import json

from app.schemas.dto.conversations import LlmToolResult
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText


def build_user_text_payload(text: MessageText) -> LlmProviderPayload:
    return LlmProviderPayload(
        json.dumps(
            {"role": "user", "content": [{"type": "text", "text": str(text)}]},
            ensure_ascii=False,
        )
    )


def build_tool_results_payload(results: list[LlmToolResult]) -> LlmProviderPayload:
    content: list[dict[str, object]] = []
    for result in results:
        content.append(
            {
                "type": "tool_result",
                "tool_use_id": str(result.call_id),
                "content": str(result.result_json),
                "is_error": result.is_error,
            }
        )

    return LlmProviderPayload(
        json.dumps({"role": "user", "content": content}, ensure_ascii=False)
    )
