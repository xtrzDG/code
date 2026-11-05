"""A model request with one tool, as the OpenAI adapter tests send it."""

import json

from app.schemas.constants.assistants import AssistantToolName, LlmEffort
from app.schemas.dto.conversations import LlmRequest, LlmToolDefinition
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import (
    LlmToolDescription,
    LlmToolInputSchemaJson,
    SystemPromptText,
)
from app.schemas.typings.conversations.strings import LlmProviderPayload

PRICE_TOOL = LlmToolDefinition(
    name=AssistantToolName.GET_PRICE,
    description=LlmToolDescription("Look up a price."),
    input_schema_json=LlmToolInputSchemaJson(
        json.dumps(
            {
                "type": "object",
                "properties": {"item_name": {"type": "string"}},
                "required": ["item_name"],
                "additionalProperties": False,
            }
        )
    ),
)


def build_request(
    transcript: list[LlmProviderPayload],
    effort: LlmEffort = LlmEffort.LOW,
) -> LlmRequest:
    return LlmRequest(
        model_id=LlmModelId("gpt-5-mini"),
        system_prompt=SystemPromptText("You are the AI assistant of Sakhli."),
        tools=[PRICE_TOOL],
        transcript=transcript,
        max_output_tokens=LlmMaxOutputTokens(4000),
        effort=effort,
    )
