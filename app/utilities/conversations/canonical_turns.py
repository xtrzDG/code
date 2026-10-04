"""
The provider-neutral form of an assistant turn: its text and tool calls as
`text` and `tool_use` blocks, without a provider's reasoning, signatures or
item ids. Every provider adapter reads it (OpenAI converts it, Anthropic
takes it as it is), so a conversation can continue on a model of another
provider when its own fails.
"""

import json
from collections.abc import Sequence

from app.schemas.dto.conversations import LlmToolCall
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText
from app.utilities.conversations.llm_transcript import (
    ASSISTANT_ROLE,
    TEXT_BLOCK_TYPE,
    TOOL_USE_BLOCK_TYPE,
    decode_tool_arguments,
)


def build_canonical_assistant_payload(
    text: MessageText | None,
    tool_calls: Sequence[LlmToolCall],
) -> LlmProviderPayload | None:
    """
    The canonical assistant turn of a response; None when it said nothing
    and called nothing (no provider accepts an empty assistant turn).
    """

    content: list[dict[str, object]] = []
    if text is not None and str(text).strip() != "":
        content.append({"type": TEXT_BLOCK_TYPE, "text": str(text)})

    content.extend(
        {
            "type": TOOL_USE_BLOCK_TYPE,
            "id": str(call.call_id),
            "name": str(call.tool_name),
            "input": decode_tool_arguments(str(call.input_json)),
        }
        for call in tool_calls
    )
    if not content:
        return None

    return LlmProviderPayload(
        json.dumps({"role": ASSISTANT_ROLE, "content": content}, ensure_ascii=False)
    )
