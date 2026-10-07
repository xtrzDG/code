"""A voice tool answers the agent within its deadline, also when it hangs."""

import json
import threading
from typing import NoReturn

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.voice.elevenlabs_tool_config import TOOL_RESPONSE_TIMEOUT_SECONDS
from app.gateways.http import voice_routes
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.voice_routes import build_voice_router
from app.schemas.dto.conversations import VoiceToolCallResult
from app.schemas.dto.voice_webhooks import VoiceToolWebhookRequest
from app.schemas.typings.conversations.strings import LlmToolResultJson
from app.utilities.channels.channel_endpoints import (
    VOICE_BUSINESS_ID_HEADER,
    VOICE_TOOL_SECRET_HEADER,
)

HEADERS: dict[str, str] = {
    VOICE_BUSINESS_ID_HEADER: "business_0f8f6bd6-e9b2-4a4c-8b8c-3c1f2a7e9d10",
    VOICE_TOOL_SECRET_HEADER: "tool-secret",
}
TOOL_PATH: str = "/v1/voice/tools/check_availability"


# Longer than any test waits: a tool held this long means the route waited.
HELD_TOOL_SECONDS: float = 10.0


class ToolOperator:
    """A tool that answers at once, or holds until the test `release`s it."""

    def __init__(self, release: threading.Event | None = None) -> None:
        self.release: threading.Event | None = release
        self.finished = threading.Event()

    def operate(self, input_data: VoiceToolWebhookRequest) -> VoiceToolCallResult:
        del input_data
        if self.release is not None:
            self.release.wait(timeout=HELD_TOOL_SECONDS)
        self.finished.set()
        return VoiceToolCallResult(result_json=LlmToolResultJson('{"slots": []}'))


class UnusedOperator:
    def operate(self, input_data: object) -> NoReturn:
        raise AssertionError(f"Not called in this test: {input_data!r}")


def build_client(operator: ToolOperator) -> TestClient:
    application = FastAPI()
    install_error_handlers(application)
    application.include_router(
        build_voice_router(
            voice_tool_operator=operator,
            call_initiation_operator=UnusedOperator(),
            post_call_operator=UnusedOperator(),
        )
    )
    return TestClient(application)


def test_a_fast_tool_answers_with_its_result() -> None:
    response = build_client(ToolOperator()).post(
        TOOL_PATH, headers=HEADERS, content=b"{}"
    )

    assert response.status_code == 200
    assert response.json() == {"slots": []}


def test_a_tool_past_its_deadline_tells_the_agent_to_hand_over(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(voice_routes, "VOICE_TOOL_DEADLINE_SECONDS", 0.2)
    release = threading.Event()
    operator = ToolOperator(release)

    response = build_client(operator).post(TOOL_PATH, headers=HEADERS, content=b"{}")
    # The agent got its answer while the tool was still held.
    answered_first: bool = not operator.finished.is_set()
    release.set()

    assert response.status_code == 200
    assert "colleague will check" in json.loads(response.text)["error"]
    assert answered_first
    assert "did not finish within" in caplog.text
    # The tool itself is not cut off: it finishes in its own thread.
    assert operator.finished.wait(timeout=HELD_TOOL_SECONDS)


def test_the_deadline_stays_below_the_voice_platform_timeout() -> None:
    assert voice_routes.VOICE_TOOL_DEADLINE_SECONDS < TOOL_RESPONSE_TIMEOUT_SECONDS
