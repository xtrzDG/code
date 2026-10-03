import json
from collections.abc import Sequence

from openai.types.responses import (
    Response,
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
)

from app.adapters.llm.llm_call_limits import call_max_retries, call_timeout_seconds
from app.adapters.llm.llm_payloads import (
    build_tool_results_payload,
    build_user_media_payload,
    build_user_text_payload,
)
from app.adapters.llm.openai_input_items import build_openai_input_items
from app.contracts.llm import LlmAdapterContract
from app.contracts.llm_clients import OpenAiResponsesClientContract
from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.dto.conversations import (
    LlmRequest,
    LlmResponse,
    LlmToolCall,
    LlmToolDefinition,
    LlmToolResult,
)
from app.schemas.dto.media import LlmImageInput
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
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
    OPENAI_PROVIDER_MARKER,
    encode_json,
    parse_model_tool_name,
)

REASONING_EFFORTS: dict[LlmEffort, str] = {
    LlmEffort.MINIMAL: "minimal",
    LlmEffort.LOW: "low",
    LlmEffort.MEDIUM: "medium",
    LlmEffort.HIGH: "high",
}
MAX_OUTPUT_TOKENS_REASON: str = "max_output_tokens"
CONTENT_FILTER_REASON: str = "content_filter"
MESSAGE_SEPARATOR: str = "\n\n"


class OpenAiLlmAdapter(LlmAdapterContract):
    """
    Language model behind the OpenAI Responses API (the concept's default:
    gpt-5-mini in an EU data-residency project).

    User and tool-result turns are stored in the canonical format and
    converted to Responses input items on every call, deterministically.
    Assistant turns are stored as the response output items exactly as
    returned (`{"role": "assistant", "provider": "openai", "items": [...]}`,
    reasoning items with their encrypted content) and replayed unchanged.
    """

    def __init__(self, client: OpenAiResponsesClientContract) -> None:
        self._client: OpenAiResponsesClientContract = client

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
        response: Response = self._client.create_response(
            model=str(request.model_id),
            instructions=str(request.system_prompt),
            input_items=build_openai_input_items(request.transcript),
            tools=[build_openai_function_tool(tool) for tool in request.tools],
            reasoning_effort=REASONING_EFFORTS[request.effort],
            max_output_tokens=int(request.max_output_tokens),
            timeout_seconds=call_timeout_seconds(request),
            max_retries=call_max_retries(request),
        )
        return parse_openai_response(response)


def build_openai_function_tool(tool: LlmToolDefinition) -> dict[str, object]:
    """Strict function tool: the model's arguments always match the schema."""

    return {
        "type": "function",
        "name": str(tool.name),
        "description": str(tool.description),
        "parameters": json.loads(tool.input_schema_json),
        "strict": True,
    }


def parse_openai_response(response: Response) -> LlmResponse:
    """
    Normalize a Responses API result.

    Raises:
        LlmRefusedError: the model refused or the output was filtered.
        ExternalServiceError: the response failed or named an unknown tool.
    """

    if response.status == "failed" or response.error is not None:
        error_code: str = "unknown" if response.error is None else response.error.code
        raise ExternalServiceError(f"OpenAI response failed: {error_code}.")

    texts: list[str] = []
    refusals: list[str] = []
    tool_calls: list[LlmToolCall] = []
    for item in response.output:
        if isinstance(item, ResponseOutputMessage):
            message_parts: list[str] = []
            for part in item.content:
                if isinstance(part, ResponseOutputText):
                    message_parts.append(part.text)
                else:
                    refusals.append(part.refusal)

            if message_parts:
                texts.append("".join(message_parts))
        elif isinstance(item, ResponseFunctionToolCall):
            tool_calls.append(
                LlmToolCall(
                    call_id=LlmToolCallId(item.call_id),
                    tool_name=parse_model_tool_name(item.name),
                    input_json=LlmToolInputJson(item.arguments),
                )
            )

    incomplete_reason: str | None = (
        None
        if response.incomplete_details is None
        else response.incomplete_details.reason
    )
    if refusals or incomplete_reason == CONTENT_FILTER_REASON:
        raise LlmRefusedError("The OpenAI model declined to answer.")

    stop_reason: LlmStopReason = LlmStopReason.END_TURN
    if response.status == "incomplete" and incomplete_reason == (
        MAX_OUTPUT_TOKENS_REASON
    ):
        stop_reason = LlmStopReason.MAX_TOKENS
    elif tool_calls:
        stop_reason = LlmStopReason.TOOL_USE

    text: str = MESSAGE_SEPARATOR.join(texts).strip()
    return LlmResponse(
        stop_reason=stop_reason,
        text=MessageText(text) if text else None,
        tool_calls=tool_calls,
        assistant_turn_payload=LlmProviderPayload(
            encode_json(
                {
                    "role": ASSISTANT_ROLE,
                    "provider": OPENAI_PROVIDER_MARKER,
                    "items": [item.to_dict(mode="json") for item in response.output],
                }
            )
        ),
        input_tokens=LlmTokenCount(
            0 if response.usage is None else response.usage.input_tokens
        ),
        output_tokens=LlmTokenCount(
            0 if response.usage is None else response.usage.output_tokens
        ),
    )
