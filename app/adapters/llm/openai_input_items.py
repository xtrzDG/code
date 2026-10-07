"""
Responses API input items of a stored transcript: canonical user turns
(text, pictures resolved to their bytes, tool results), OpenAI assistant
turns as returned, and assistant turns of another provider converted.
"""

from typing import cast

from app.schemas.typings.conversations.strings import LlmProviderPayload
from app.utilities.conversations.llm_transcript import (
    ASSISTANT_ROLE,
    OPENAI_FUNCTION_CALL_ITEM_TYPE,
    TEXT_BLOCK_TYPE,
    TOOL_RESULT_BLOCK_TYPE,
    TOOL_USE_BLOCK_TYPE,
    USER_ROLE,
    encode_json,
    is_openai_assistant_turn,
    parse_transcript_turn,
    read_object_list,
    read_string,
    read_tool_result_text,
)

IMAGE_BLOCK_TYPE: str = "image"
BASE64_SOURCE_TYPE: str = "base64"


def build_openai_input_items(
    transcript: list[LlmProviderPayload],
) -> list[dict[str, object]]:
    """
    Responses input items for a stored transcript.

    Canonical user text becomes a user message with `input_text` parts; each
    tool result becomes a `function_call_output` item. OpenAI assistant turns
    are replayed item by item; Anthropic-format assistant turns (scripted or
    from another provider) become an assistant message and `function_call`
    items, without their reasoning.
    """

    items: list[dict[str, object]] = []
    for payload in transcript:
        turn: dict[str, object] = parse_transcript_turn(payload)
        if turn["role"] == USER_ROLE:
            items.extend(convert_user_turn(turn))
        elif is_openai_assistant_turn(turn):
            items.extend(read_object_list(turn.get("items")))
        else:
            items.extend(convert_foreign_assistant_turn(turn))

    return items


def convert_user_turn(turn: dict[str, object]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    pending_parts: list[dict[str, object]] = []

    def flush_texts() -> None:
        if pending_parts:
            items.append({"role": USER_ROLE, "content": list(pending_parts)})
            pending_parts.clear()

    for block in read_object_list(turn.get("content")):
        block_type: str | None = read_string(block, "type")
        if block_type == TEXT_BLOCK_TYPE:
            text: str | None = read_string(block, "text")
            if text is not None:
                pending_parts.append({"type": "input_text", "text": text})
        elif block_type == IMAGE_BLOCK_TYPE:
            image_part: dict[str, object] | None = convert_image_block(block)
            if image_part is not None:
                pending_parts.append(image_part)
        elif block_type == TOOL_RESULT_BLOCK_TYPE:
            flush_texts()
            items.append(
                {
                    "type": "function_call_output",
                    "call_id": read_string(block, "tool_use_id") or "",
                    "output": read_tool_result_text(block),
                }
            )

    flush_texts()
    return items


def convert_image_block(block: dict[str, object]) -> dict[str, object] | None:
    """
    A picture resolved to its bytes as an `input_image` part; an image
    block still naming a stored file (never resolved) is left out.
    """

    raw_source: object = block.get("source")
    source: dict[str, object] = (
        cast(dict[str, object], raw_source) if isinstance(raw_source, dict) else {}
    )
    data: str | None = read_string(source, "data")
    media_type: str | None = read_string(source, "media_type")
    if read_string(source, "type") != BASE64_SOURCE_TYPE or not data or not media_type:
        return None

    return {
        "type": "input_image",
        "image_url": f"data:{media_type};base64,{data}",
        "detail": "auto",
    }


def convert_foreign_assistant_turn(
    turn: dict[str, object],
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for block in read_object_list(turn.get("content")):
        block_type: str | None = read_string(block, "type")
        if block_type == TEXT_BLOCK_TYPE:
            text: str | None = read_string(block, "text")
            if text:
                items.append({"role": ASSISTANT_ROLE, "content": text})
        elif block_type == TOOL_USE_BLOCK_TYPE:
            items.append(
                {
                    "type": OPENAI_FUNCTION_CALL_ITEM_TYPE,
                    "call_id": read_string(block, "id") or "",
                    "name": read_string(block, "name") or "",
                    "arguments": encode_json(block.get("input", {})),
                }
            )

    return items
