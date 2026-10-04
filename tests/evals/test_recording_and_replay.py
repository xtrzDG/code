"""Recording stores what a model answered; replay answers from the recording."""

from pathlib import Path

import pytest
from typed_time_provider import MonotonicClock, Nanoseconds

from app.adapters.llm.llm_cassette_file_store import LlmCassetteFileStore
from app.adapters.llm.recording_llm_adapter import RecordingLlmAdapter
from app.adapters.llm.replay_llm_adapter import ReplayLlmAdapter
from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.evaluation_errors import LlmCassetteMissError
from app.schemas.typings.conversations.strings import (
    LlmToolCallId,
    LlmToolResultJson,
    MessageText,
)
from app.schemas.typings.evaluations.constrained_integers import (
    LlmCassetteSampleIndex,
)
from app.schemas.typings.platform.constrained_integers import ElapsedMilliseconds
from app.utilities.llm_cassettes.cassette_keys import build_cassette_request
from tests.evals.eval_builders import llm_request, user_turn


class Observed:
    """A call observer that keeps what it was told."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def observe(
        self,
        request: LlmRequest,
        response: LlmResponse,
        elapsed: ElapsedMilliseconds,
    ) -> None:
        self.calls.append((str(response.text), int(elapsed)))


def clock() -> MonotonicClock[Nanoseconds]:
    ticks: list[int] = [0, 7_000_000, 7_000_000, 9_000_000]
    return MonotonicClock(
        preferred_time_unit_type=Nanoseconds,
        monotonic_nanosecond_factory=lambda: ticks.pop(0) if ticks else 9_000_000,
    )


def recorder(
    store: LlmCassetteFileStore, sample: int, observer: Observed | None = None
) -> RecordingLlmAdapter:
    inner = ScriptedLlmAdapter(
        lambda request: ScriptedLlmTurn(
            text=MessageText(f"answer to {len(request.transcript)} turn(s)")
        )
    )
    return RecordingLlmAdapter(
        inner, store, LlmCassetteSampleIndex(sample), clock(), observer
    )


def test_recorded_answers_are_replayed_per_sample(tmp_path: Path) -> None:
    store = LlmCassetteFileStore(tmp_path / "c.json")
    observer = Observed()
    request = llm_request([user_turn("Hi")])
    first = recorder(store, 0, observer).complete(request)
    recorder(store, 1).complete(request)

    replayed_observer = Observed()
    replay = ReplayLlmAdapter(store, LlmCassetteSampleIndex(0), replayed_observer)

    assert replay.complete(request) == first
    assert observer.calls == [("answer to 1 turn(s)", 7)]
    assert replayed_observer.calls == [("answer to 1 turn(s)", 7)]
    cassette = build_cassette_request(request)
    assert store.read_instruction(cassette.instruction_digest) == request.system_prompt
    assert store.read_tools(cassette.tools_digest) == [
        tool.name for tool in request.tools
    ]
    entry = store.find(cassette.request_digest)
    assert entry is not None and len(entry.takes) == 2


def test_a_missing_recording_raises_and_keeps_the_reason(tmp_path: Path) -> None:
    store = LlmCassetteFileStore(tmp_path / "c.json")
    recorder(store, 0).complete(llm_request([user_turn("Hi")], system_prompt="Old."))
    replay = ReplayLlmAdapter(store, LlmCassetteSampleIndex(0))

    with pytest.raises(LlmCassetteMissError, match="instruction changed"):
        replay.complete(llm_request([user_turn("Hi")], system_prompt="New."))

    assert len(replay.misses) == 1
    assert "-Old." in str(replay.misses[0].reason)


def test_a_request_recorded_for_other_samples_names_the_sample(tmp_path: Path) -> None:
    store = LlmCassetteFileStore(tmp_path / "c.json")
    request = llm_request([user_turn("Hi")])
    recorder(store, 0).complete(request)

    with pytest.raises(LlmCassetteMissError, match="not for sample 3"):
        ReplayLlmAdapter(store, LlmCassetteSampleIndex(2)).complete(request)


def test_failed_calls_are_not_recorded(tmp_path: Path) -> None:
    store = LlmCassetteFileStore(tmp_path / "c.json")
    adapter = RecordingLlmAdapter(
        ScriptedLlmAdapter.from_turns([]),
        store,
        LlmCassetteSampleIndex(0),
        clock(),
    )

    with pytest.raises(ExternalServiceError):
        adapter.complete(llm_request([user_turn("Hi")]))

    assert store.list_entries() == []


def test_both_adapters_build_canonical_turns(tmp_path: Path) -> None:
    store = LlmCassetteFileStore(tmp_path / "c.json")
    replay = ReplayLlmAdapter(store, LlmCassetteSampleIndex(0))
    recording = recorder(store, 0)
    results = [
        LlmToolResult(
            call_id=LlmToolCallId("toolu_1"), result_json=LlmToolResultJson("{}")
        )
    ]

    assert replay.build_user_text_turn(MessageText("Hi")) == (
        recording.build_user_text_turn(MessageText("Hi"))
    )
    assert replay.build_tool_results_turn(results) == (
        recording.build_tool_results_turn(results)
    )
