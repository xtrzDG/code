import json

from anthropic.types.beta import BetaMessage, BetaTextBlock, BetaToolUseBlock

from app.adapters.llm.llm_payloads import (
    build_tool_results_payload,
    build_user_text_payload,
)
from app.contracts.llm import LlmAdapterContract
from app.contracts.llm_clients import AnthropicMessagesClientContract
from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.dto.conversations import (
    LlmRequest,
    LlmResponse,
    LlmToolCall,
    LlmToolDefinition,
    LlmToolResult,
)
from app.schemas.exceptions.application_errors import (
    LlmRefusedError,
)
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    LlmToolCallId,
    LlmToolInputJson,
    MessageText,
)
from app.utilities.conversations.llm_transcript import (
    ASSISTANT_ROLE,
    OPENAI_FUNCTION_CALL_ITEM_TYPE,
    OPENAI_MESSAGE_ITEM_TYPE,
    TEXT_BLOCK_TYPE,
    TOOL_USE_BLOCK_TYPE,
    decode_tool_arguments,
    encode_json,
    is_openai_assistant_turn,
    parse_model_tool_name,
    parse_transcript_turn,
    read_object_list,
    read_openai_output_texts,
    read_string,
)

# The Messages API has no "minimal" effort; the lowest level is "low".
OUTPUT_EFFORTS: dict[LlmEffort, str] = {
    LlmEffort.MINIMAL: "low",
    LlmEffort.LOW: "low",
    LlmEffort.MEDIUM: "medium",
    LlmEffort.HIGH: "high",
}
STOP_REASONS: dict[str, LlmStopReason] = {
    "end_turn": LlmStopReason.END_TURN,
    "stop_sequence": LlmStopReason.END_TURN,
    "tool_use": LlmStopReason.TOOL_USE,
    "max_tokens": LlmStopReason.MAX_TOKENS,
    "model_context_window_exceeded": LlmStopReason.MAX_TOKENS,
    "pause_turn": LlmStopReason.PAUSE_TURN,
}
REFUSAL_STOP_REASON: str = "refusal"
MESSAGE_SEPARATOR: str = "\n\n"


class AnthropicLlmAdapter(LlmAdapterContract):
    """
    Language model behind the Anthropic Messages API (the alternative
    provider).

    The frozen system prompt is cached; canonical user turns are sent as
    they are stored and assistant turns are stored as the response content
    blocks (thinking and fallback blocks included) and replayed unchanged.
    A refusal of the model and of its server-side fallbacks raises
    LlmRefusedError before any content is read.
    """

    def __init__(self, client: AnthropicMessagesClientContract) -> None:
        self._client: AnthropicMessagesClientContract = client

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        return build_user_text_payload(text)

    def build_tool_results_turn(
        self,
        results: list[LlmToolResult],
    ) -> LlmProviderPayload:
        return build_tool_results_payload(results)

    def complete(self, request: LlmRequest) -> LlmResponse:
        message: BetaMessage = self._client.create_message(
            model=str(request.model_id),
            max_tokens=int(request.max_output_tokens),
            system=[
                {
                    "type": "text",
                    "text": str(request.system_prompt),
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[build_anthropic_tool(tool) for tool in request.tools],
            messages=build_anthropic_messages(request.transcript),
            effort=OUTPUT_EFFORTS[request.effort],
        )
        return parse_anthropic_message(message)


def build_anthropic_tool(tool: LlmToolDefinition) -> dict[str, object]:
    """Strict tool: the model's input always validates against the schema."""

    return {
        "name": str(tool.name),
        "description": str(tool.description),
        "input_schema": json.loads(tool.input_schema_json),
        "strict": True,
    }


def build_anthropic_messages(
    transcript: list[LlmProviderPayload],
) -> list[dict[str, object]]:
    """
    Messages for a stored transcript: canonical user turns and Anthropic
    assistant turns as stored; OpenAI assistant turns converted to text and
    tool_use blocks (their reasoning cannot be replayed on another provider).
    """

    messages: list[dict[str, object]] = []
    for payload in transcript:
        turn: dict[str, object] = parse_transcript_turn(payload)
        if is_openai_assistant_turn(turn):
            content: list[dict[str, object]] = convert_openai_items(turn)
            if content:
                messages.append({"role": ASSISTANT_ROLE, "content": content})
            continue

        messages.append({"role": turn["role"], "content": turn.get("content", [])})

    return messages


def convert_openai_items(turn: dict[str, object]) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    for item in read_object_list(turn.get("items")):
        item_type: str | None = read_string(item, "type")
        if item_type == OPENAI_MESSAGE_ITEM_TYPE:
            for text in read_openai_output_texts(item):
                if text:
                    blocks.append({"type": TEXT_BLOCK_TYPE, "text": text})
        elif item_type == OPENAI_FUNCTION_CALL_ITEM_TYPE:
            blocks.append(
                {
                    "type": TOOL_USE_BLOCK_TYPE,
                    "id": read_string(item, "call_id") or "",
                    "name": read_string(item, "name") or "",
                    "input": decode_tool_arguments(
                        read_string(item, "arguments") or "{}"
                    ),
                }
            )

    return blocks


def parse_anthropic_message(message: BetaMessage) -> LlmResponse:
    """
    Normalize a Messages API result; the stop reason is checked first.

    Raises:
        LlmRefusedError: the model and its fallbacks declined.
        ExternalServiceError: the model called an unknown tool.
    """

    if message.stop_reason == REFUSAL_STOP_REASON:
        raise LlmRefusedError("The Anthropic model declined to answer.")

    texts: list[str] = []
    tool_calls: list[LlmToolCall] = []
    for block in message.content:
        if isinstance(block, BetaTextBlock):
            texts.append(block.text)
        elif isinstance(block, BetaToolUseBlock):
            tool_calls.append(
                LlmToolCall(
                    call_id=LlmToolCallId(block.id),
                    tool_name=parse_model_tool_name(block.name),
                    input_json=LlmToolInputJson(encode_json(block.input)),
                )
            )

    stop_reason: LlmStopReason = STOP_REASONS.get(
        message.stop_reason or "",
        LlmStopReason.OTHER,
    )
    if tool_calls and stop_reason is not LlmStopReason.MAX_TOKENS:
        stop_reason = LlmStopReason.TOOL_USE

    usage = message.usage
    input_tokens: int = (
        usage.input_tokens
        + (usage.cache_creation_input_tokens or 0)
        + (usage.cache_read_input_tokens or 0)
    )
    text: str = MESSAGE_SEPARATOR.join(part for part in texts if part).strip()
    return LlmResponse(
        stop_reason=stop_reason,
        text=MessageText(text) if text else None,
        tool_calls=tool_calls,
        assistant_turn_payload=LlmProviderPayload(
            encode_json(
                {
                    "role": ASSISTANT_ROLE,
                    "content": [
                        block.to_dict(mode="json") for block in message.content
                    ],
                }
            )
        ),
        input_tokens=LlmTokenCount(input_tokens),
        output_tokens=LlmTokenCount(usage.output_tokens),
    )
