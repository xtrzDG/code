"""Cassettes are JSON files that survive a round trip in a stable order."""

from pathlib import Path

import pytest

from app.adapters.llm.llm_cassette_file_store import LlmCassetteFileStore
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.llm_cassettes import LlmCassetteRecording, LlmCassetteTake
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.evaluations.constrained_integers import (
    LlmCassetteSampleIndex,
)
from app.schemas.typings.platform.constrained_integers import ElapsedMilliseconds
from app.utilities.llm_cassettes.cassette_keys import build_cassette_request
from tests.evals.eval_builders import llm_request, llm_response, user_turn


def take(text: str, sample: int = 0) -> LlmCassetteTake:
    return LlmCassetteTake(
        sample_index=LlmCassetteSampleIndex(sample),
        response=llm_response(text),
        elapsed=ElapsedMilliseconds(12),
    )


def test_a_saved_cassette_reads_back(tmp_path: Path) -> None:
    path = tmp_path / "cassettes" / "hotel.json"
    store = LlmCassetteFileStore(path)
    assert store.recording() is None
    first = build_cassette_request(llm_request([user_turn("b")]))
    second = build_cassette_request(llm_request([user_turn("a")]))
    store.record(first, take("one"))
    store.record(first, take("again", sample=1))
    store.record(first, take("replaced"))
    store.record(second, take("two"))
    store.remember_instruction(first.instruction_digest, SystemPromptText("Be kind."))
    store.remember_tools(first.tools_digest, [AssistantToolName.GET_PRICE])
    store.set_recording(
        LlmCassetteRecording(
            assistant_model_id=LlmModelId("scripted"),
            customer_model_id=LlmModelId("scripted"),
        )
    )
    store.save()

    loaded = LlmCassetteFileStore(path)

    entry = loaded.find(first.key)
    assert entry is not None
    assert [str(t.response.text) for t in entry.takes] == ["replaced", "again"]
    assert len(loaded.list_entries()) == 2
    assert loaded.read_instruction(first.instruction_digest) == "Be kind."
    assert loaded.read_tools(first.tools_digest) == [AssistantToolName.GET_PRICE]
    recording = loaded.recording()
    assert recording is not None and recording.assistant_model_id == "scripted"
    # Saving again writes the same bytes: re-recordings diff cleanly.
    before = path.read_text(encoding="utf-8")
    loaded.save()
    assert path.read_text(encoding="utf-8") == before


def test_a_fresh_store_ignores_what_the_file_holds(tmp_path: Path) -> None:
    path = tmp_path / "hotel.json"
    store = LlmCassetteFileStore(path)
    store.record(build_cassette_request(llm_request([user_turn("a")])), take("x"))
    store.save()

    assert LlmCassetteFileStore(path, is_fresh=True).list_entries() == []


def test_an_unreadable_or_foreign_file_is_refused(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    old = tmp_path / "old.json"
    old.write_text('{"format_version": 7}', encoding="utf-8")

    with pytest.raises(ValidationFailedError, match="not a readable cassette"):
        LlmCassetteFileStore(broken)

    with pytest.raises(ValidationFailedError, match="Record the cassettes again"):
        LlmCassetteFileStore(old)
