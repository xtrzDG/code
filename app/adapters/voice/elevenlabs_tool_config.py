"""The ElevenLabs webhook tool that forwards one assistant tool to this backend."""

from app.contracts.channel_clients import JsonObject
from app.schemas.dto.conversations import LlmToolDefinition
from app.utilities.channels.channel_endpoints import (
    build_voice_tool_path,
    join_public_url,
)
from app.utilities.channels.json_values import parse_json_object
from app.utilities.channels.voice_tool_schemas import convert_tool_schema

# The concept's target is a tool answer within a second; the timeout only
# bounds a stuck request so the agent can apologise and move on.
TOOL_RESPONSE_TIMEOUT_SECONDS: int = 10
ARGUMENTS_DESCRIPTION: str = "Arguments of the tool call."
LANGUAGE_DESCRIPTION: str = (
    "BCP 47 tag of the language the caller speaks right now, such as en, ka, "
    "ru, he or pt-BR."
)
REQUEST_BODY_DESCRIPTION: str = "Tool call of the business assistant."


def build_tool_config(
    tool: LlmToolDefinition,
    base_url: str,
    request_headers: JsonObject,
) -> JsonObject:
    """ElevenLabs webhook tool that forwards one assistant tool to this backend."""

    input_schema: JsonObject = parse_json_object(str(tool.input_schema_json)) or {}
    return {
        "type": "webhook",
        "name": tool.name.value,
        "description": str(tool.description),
        "response_timeout_secs": TOOL_RESPONSE_TIMEOUT_SECONDS,
        "api_schema": {
            "url": join_public_url(base_url, build_voice_tool_path(tool.name)),
            "method": "POST",
            "request_headers": dict(request_headers),
            "request_body_schema": {
                "type": "object",
                "description": REQUEST_BODY_DESCRIPTION,
                "properties": {
                    "arguments": convert_tool_schema(
                        input_schema, ARGUMENTS_DESCRIPTION
                    ),
                    "conversation_id": {
                        "type": "string",
                        "dynamic_variable": "system__conversation_id",
                    },
                    "caller_id": {
                        "type": "string",
                        "dynamic_variable": "system__caller_id",
                    },
                    "language": {"type": "string", "description": LANGUAGE_DESCRIPTION},
                },
                "required": ["arguments", "conversation_id"],
            },
        },
    }
