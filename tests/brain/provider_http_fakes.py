"""
Provider SDKs talking to scripted HTTP responses (no network).

The real OpenAI and Anthropic SDK clients are built on `httpx2`; their HTTP
client gets a `MockTransport` that records request bodies and replays canned
JSON, so tests see exactly what goes over the wire.
"""

import json
from dataclasses import dataclass, field
from typing import Any, cast

import anthropic
import httpx2
import openai

from app.clients.anthropic.anthropic_messages_client import AnthropicMessagesClient
from app.clients.openai.openai_responses_client import OpenAiResponsesClient
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import PlatformIdentifier

OPENAI_EU_BASE_URL: str = "https://eu.api.openai.com/v1"
ANTHROPIC_TEST_BASE_URL: str = "https://api.anthropic.test"


@dataclass
class ScriptedHttp:
    """Replays responses in order and remembers every request."""

    responses: list[httpx2.Response]
    requests: list[httpx2.Request] = field(default_factory=list[httpx2.Request])

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("No scripted HTTP response left.")

        return self.responses.pop(0)

    def body(self, index: int) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self.requests[index].content))

    def build_http_client(self) -> httpx2.Client:
        return httpx2.Client(transport=httpx2.MockTransport(self.handle))


def build_openai_client(
    http: ScriptedHttp,
    project_id: str | None = "proj_eu_restaurants",
) -> OpenAiResponsesClient:
    def build_sdk() -> openai.OpenAI:
        return openai.OpenAI(
            api_key="sk-test",
            base_url=OPENAI_EU_BASE_URL,
            project=project_id,
            http_client=http.build_http_client(),
            max_retries=0,
        )

    return OpenAiResponsesClient(
        base_url=PublicBaseUrl(OPENAI_EU_BASE_URL),
        project_id=None if project_id is None else PlatformIdentifier(project_id),
        sdk_factory=build_sdk,
    )


def build_anthropic_client(http: ScriptedHttp) -> AnthropicMessagesClient:
    def build_sdk() -> anthropic.Anthropic:
        return anthropic.Anthropic(
            api_key="sk-ant-test",
            base_url=ANTHROPIC_TEST_BASE_URL,
            http_client=http.build_http_client(),
            max_retries=0,
        )

    return AnthropicMessagesClient(sdk_factory=build_sdk)


def openai_response(
    output: list[dict[str, Any]],
    *,
    status: str = "completed",
    incomplete_reason: str | None = None,
    input_tokens: int = 1200,
    output_tokens: int = 80,
) -> httpx2.Response:
    return httpx2.Response(
        200,
        json={
            "id": "resp_test",
            "object": "response",
            "created_at": 1759312800,
            "model": "gpt-5-mini-2025-08-07",
            "status": status,
            "error": None,
            "incomplete_details": (
                None if incomplete_reason is None else {"reason": incomplete_reason}
            ),
            "output": output,
            "parallel_tool_calls": True,
            "tool_choice": "auto",
            "tools": [],
            "usage": {
                "input_tokens": input_tokens,
                "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
                "output_tokens": output_tokens,
                "output_tokens_details": {"reasoning_tokens": 16},
                "total_tokens": input_tokens + output_tokens,
            },
        },
    )


def openai_reasoning_item(item_id: str = "rs_1") -> dict[str, Any]:
    return {
        "type": "reasoning",
        "id": item_id,
        "summary": [],
        "encrypted_content": f"gAAAA-encrypted-{item_id}",
    }


def openai_message_item(text: str, item_id: str = "msg_1") -> dict[str, Any]:
    return {
        "type": "message",
        "id": item_id,
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": text, "annotations": []}],
    }


def openai_function_call_item(
    name: str,
    arguments: dict[str, Any],
    call_id: str = "call_1",
) -> dict[str, Any]:
    return {
        "type": "function_call",
        "id": f"fc_{call_id}",
        "call_id": call_id,
        "name": name,
        "arguments": json.dumps(arguments, ensure_ascii=False),
        "status": "completed",
    }


def anthropic_message(
    content: list[dict[str, Any]],
    stop_reason: str = "end_turn",
    *,
    input_tokens: int = 100,
    cache_read_tokens: int = 900,
    output_tokens: int = 40,
) -> httpx2.Response:
    return httpx2.Response(
        200,
        json={
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": "claude-opus-5-5",
            "content": content,
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_input_tokens": cache_read_tokens,
                "cache_creation_input_tokens": 0,
            },
        },
    )


def error_response(status_code: int) -> httpx2.Response:
    return httpx2.Response(
        status_code,
        json={"error": {"type": "error", "message": "scripted failure"}},
    )
