"""
Reading stored transcript turns.

Turns are JSON objects: canonical user turns (`{"role": "user", "content":
[text and tool_result blocks]}`, see app/adapters/llm/llm_payloads.py),
Anthropic-format assistant turns (`{"role": "assistant", "content": [...]}`)
and OpenAI assistant turns (`{"role": "assistant", "provider": "openai",
"items": [...]}`). Provider adapters convert them; nothing here talks to a
provider.
"""

import json
from typing import cast

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.conversations.strings import LlmProviderPayload

USER_ROLE: str = "user"
ASSISTANT_ROLE: str = "assistant"
OPENAI_PROVIDER_MARKER: str = "openai"
TEXT_BLOCK_TYPE: str = "text"
TOOL_USE_BLOCK_TYPE: str = "tool_use"
TOOL_RESULT_BLOCK_TYPE: str = "tool_result"
OPENAI_MESSAGE_ITEM_TYPE: str = "message"
OPENAI_FUNCTION_CALL_ITEM_TYPE: str = "function_call"
OPENAI_OUTPUT_TEXT_TYPE: str = "output_text"


def parse_transcript_turn(payload: LlmProviderPayload) -> dict[str, object]:
    """
    Decode one stored turn.

    Raises:
        ExternalServiceError: the payload is not a JSON object with a role.
    """

    try:
        decoded: object = json.loads(payload)
    except json.JSONDecodeError as error:
        raise ExternalServiceError("A transcript turn is not valid JSON.") from error

    if not isinstance(decoded, dict):
        raise ExternalServiceError("A transcript turn is not a JSON object.")

    turn: dict[str, object] = cast(dict[str, object], decoded)
    if turn.get("role") not in (USER_ROLE, ASSISTANT_ROLE):
        raise ExternalServiceError("A transcript turn has an unknown role.")

    return turn


def is_openai_assistant_turn(turn: dict[str, object]) -> bool:
    """True for assistant turns stored verbatim from the OpenAI Responses API."""

    return (
        turn.get("role") == ASSISTANT_ROLE
        and turn.get("provider") == OPENAI_PROVIDER_MARKER
    )


def read_object_list(value: object) -> list[dict[str, object]]:
    """JSON objects of a JSON array; other elements are skipped."""

    if not isinstance(value, list):
        return []

    objects: list[dict[str, object]] = []
    for element in cast(list[object], value):
        if isinstance(element, dict):
            objects.append(cast(dict[str, object], element))

    return objects


def read_string(mapping: dict[str, object], key: str) -> str | None:
    value: object = mapping.get(key)
    return value if isinstance(value, str) else None


def read_tool_result_text(block: dict[str, object]) -> str:
    """Content of a canonical tool_result block (a string or text blocks)."""

    content: object = block.get("content")
    if isinstance(content, str):
        return content

    return "".join(
        text
        for text_block in read_object_list(content)
        if (text := read_string(text_block, "text")) is not None
    )


def read_openai_output_texts(item: dict[str, object]) -> list[str]:
    """`output_text` parts of an OpenAI `message` output item."""

    return [
        text
        for part in read_object_list(item.get("content"))
        if part.get("type") == OPENAI_OUTPUT_TEXT_TYPE
        and (text := read_string(part, "text")) is not None
    ]


def decode_tool_arguments(arguments: str) -> dict[str, object]:
    """Tool arguments as a JSON object; malformed arguments become {}."""

    try:
        decoded: object = json.loads(arguments)
    except json.JSONDecodeError:
        return {}

    return cast(dict[str, object], decoded) if isinstance(decoded, dict) else {}


def encode_json(value: object) -> str:
    """Compact, deterministic JSON that keeps non-Latin text readable."""

    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def parse_model_tool_name(raw_tool_name: str) -> AssistantToolName:
    """
    Tool named by the model.

    Raises:
        ExternalServiceError: the model named a tool that does not exist.
    """

    try:
        return AssistantToolName(raw_tool_name)
    except ValueError as error:
        raise ExternalServiceError(
            f"The model called an unknown tool {raw_tool_name!r}."
        ) from error
