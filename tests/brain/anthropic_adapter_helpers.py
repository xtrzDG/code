"""A model request with one tool, as the Anthropic adapter tests send it."""

import json

from app.schemas.constants.assistants import AssistantToolName, LlmEffort
from app.schemas.dto.conversations import (
    LlmRequest,
    LlmToolDefinition,
)
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import (
    LlmToolDescription,
    LlmToolInputSchemaJson,
    SystemPromptText,
)
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
)

AVAILABILITY_TOOL = LlmToolDefinition(
    name=AssistantToolName.CHECK_AVAILABILITY,
    description=LlmToolDescription("Check free slots."),
    input_schema_json=LlmToolInputSchemaJson(
        json.dumps(
            {
                "type": "object",
                "properties": {"date": {"type": "string"}},
                "required": ["date"],
                "additionalProperties": False,
            }
        )
    ),
)


def build_request(
    transcript: list[LlmProviderPayload],
    effort: LlmEffort = LlmEffort.MEDIUM,
) -> LlmRequest:
    return LlmRequest(
        model_id=LlmModelId("claude-opus-5-5"),
        system_prompt=SystemPromptText("You are the AI assistant of Beit Kafe."),
        tools=[AVAILABILITY_TOOL],
        transcript=transcript,
        max_output_tokens=LlmMaxOutputTokens(16000),
        effort=effort,
    )
