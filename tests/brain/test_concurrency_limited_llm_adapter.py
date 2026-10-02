"""At most LLM_MAX_CONCURRENCY model calls of one process at once."""

import threading
import time

import pytest

from app.adapters.llm.concurrency_limited_llm_adapter import (
    ConcurrencyLimitedLlmAdapter,
)
from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.constrained_integers import (
    LlmCallTimeoutSeconds,
    LlmConcurrencyLimit,
)
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    MessageText,
)
from tests.brain.openai_adapter_helpers import build_request


class SlowModel(ScriptedLlmAdapter):
    """Answers after `seconds`, counting the calls running at once."""

    def __init__(self, seconds: float) -> None:
        super().__init__(lambda _request: ScriptedLlmTurn(text=MessageText("Hi")))
        self._seconds: float = seconds
        self._guard: threading.Lock = threading.Lock()
        self.running: int = 0
        self.most_at_once: int = 0

    def complete(self, request: LlmRequest) -> LlmResponse:
        with self._guard:
            self.running += 1
            self.most_at_once = max(self.most_at_once, self.running)
        try:
            time.sleep(self._seconds)
            return super().complete(request)
        finally:
            with self._guard:
                self.running -= 1


def limited(model: SlowModel, places: int, wait: int) -> ConcurrencyLimitedLlmAdapter:
    return ConcurrencyLimitedLlmAdapter(
        inner_adapter=model,
        max_concurrency=LlmConcurrencyLimit(places),
        wait_seconds=LlmCallTimeoutSeconds(wait),
    )


def request_for(adapter: ConcurrencyLimitedLlmAdapter) -> LlmRequest:
    return build_request([adapter.build_user_text_turn(MessageText("Hello"))])


def test_calls_beyond_the_limit_wait_for_a_free_place() -> None:
    model = SlowModel(0.1)
    adapter = limited(model, places=2, wait=5)
    replies: list[LlmResponse] = []
    callers = [
        threading.Thread(
            target=lambda: replies.append(adapter.complete(request_for(adapter)))
        )
        for _ in range(6)
    ]

    for caller in callers:
        caller.start()
    for caller in callers:
        caller.join()

    assert len(replies) == 6
    assert model.most_at_once == 2


def test_a_call_that_finds_no_place_in_time_fails_like_a_provider_error() -> None:
    model = SlowModel(1.6)
    adapter = limited(model, places=1, wait=1)
    holder = threading.Thread(target=lambda: adapter.complete(request_for(adapter)))
    holder.start()
    time.sleep(0.1)

    with pytest.raises(ExternalServiceError, match="LLM_MAX_CONCURRENCY"):
        adapter.complete(request_for(adapter))

    holder.join()
    # The place came back: the next call runs.
    assert adapter.complete(request_for(adapter)) is not None


def test_building_turns_takes_no_place() -> None:
    model = SlowModel(0.0)
    adapter = limited(model, places=1, wait=1)
    results: list[LlmToolResult] = []

    assert isinstance(
        adapter.build_user_text_turn(MessageText("Hi")), LlmProviderPayload
    )
    assert adapter.build_tool_results_turn(results) == model.build_tool_results_turn(
        results
    )
