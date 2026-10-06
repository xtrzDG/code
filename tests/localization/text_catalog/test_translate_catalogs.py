import json
from collections.abc import Callable
from pathlib import Path

import pytest

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.containers.app import AppContainer
from app.registries.localization.text_catalog_registry import TextCatalogRegistry
from app.schemas.constants.localization import CabinetLanguage, TextReviewStatus
from app.schemas.dto.conversations import LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import OwnerTextKey
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from scripts.catalog_translation.owner_catalog_files import load_catalog
from scripts.catalog_translation.text_drafting import OwnerTextDrafter
from scripts.translate_catalogs import configured_drafter, main
from tests.e2e.workshop_container import replace_provider
from tests.localization.text_catalog.catalog_builders import (
    ENGLISH_TEXTS,
    write_catalog,
)

MODEL: LlmModelId = LlmModelId("claude-haiku-4-5")
WITHOUT_PLAN_AND_NOTICE: dict[str, str] = {
    key: value
    for key, value in ENGLISH_TEXTS.items()
    if key not in {"plans.chat.name", "billing.notice"}
}


def asked_texts(request: LlmRequest) -> dict[str, str]:
    """The English texts of a request (the JSON of its user turn)."""

    turn = json.loads(str(request.transcript[0]))
    texts: dict[str, str] = json.loads(turn["content"][0]["text"])
    return texts


def model_answering(translate: Callable[[str], str]) -> ScriptedLlmAdapter:
    def respond(request: LlmRequest) -> ScriptedLlmTurn:
        answer = {key: translate(value) for key, value in asked_texts(request).items()}
        return ScriptedLlmTurn(text=MessageText(json.dumps(answer, ensure_ascii=False)))

    return ScriptedLlmAdapter(respond)


def factory(model: ScriptedLlmAdapter) -> Callable[[], OwnerTextDrafter]:
    return lambda: OwnerTextDrafter(model, MODEL)


def never_called() -> OwnerTextDrafter:
    raise AssertionError("no text was missing, so no model is needed")


def read_file(directory: Path, language: str) -> dict[str, object]:
    payload: dict[str, object] = json.loads(
        (directory / f"{language}.json").read_text(encoding="utf-8")
    )
    return payload


def test_check_lists_each_language_and_fails_on_a_missing_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_catalog(tmp_path, {"ka": WITHOUT_PLAN_AND_NOTICE})

    assert main(["backend", "check"], tmp_path, never_called) == 1

    lines: list[str] = capsys.readouterr().out.splitlines()
    assert lines == [
        "ka: 2/4 texts, 2 missing, 0 waiting for review",
        "ru: 4/4 texts, 0 missing, 0 waiting for review",
        "en: 4/4 texts, 0 missing, 0 waiting for review",
        "he: 4/4 texts, 0 missing, 4 waiting for review",
        "de: 4/4 texts, 0 missing, 4 waiting for review",
    ]


def test_check_passes_a_complete_catalog(tmp_path: Path) -> None:
    write_catalog(tmp_path)

    assert main(["backend", "check"], tmp_path, never_called) == 0


def test_drafts_in_a_reviewed_file_are_named_for_review(tmp_path: Path) -> None:
    write_catalog(tmp_path, {"ka": WITHOUT_PLAN_AND_NOTICE})
    model = model_answering(lambda english: f"KA {english}")

    assert main(["backend", "draft", "--language", "ka"], tmp_path, factory(model)) == 0

    written = read_file(tmp_path, "ka")
    assert written["review_status"] == "reviewed"
    assert list(written["texts"]) == list(ENGLISH_TEXTS)  # type: ignore[call-overload]
    assert written["draft_keys"] == ["plans.chat.name", "billing.notice"]
    catalog = load_catalog(tmp_path)
    registry = TextCatalogRegistry(catalog)
    assert registry.list_missing_keys(CabinetLanguage.GEORGIAN) == []
    assert (
        registry.review_status(OwnerTextKey("billing.notice"), CabinetLanguage.GEORGIAN)
        is TextReviewStatus.NEEDS_REVIEW
    )
    assert (
        registry.review_status(
            OwnerTextKey("niches.cafe.handoff_rules.1"), CabinetLanguage.GEORGIAN
        )
        is TextReviewStatus.REVIEWED
    )
    assert catalog.files[CabinetLanguage.GEORGIAN].texts[
        OwnerTextKey("billing.notice")
    ] == ("KA {business}: pay {amount}.")


def test_the_request_names_the_language_and_sends_only_missing_texts(
    tmp_path: Path,
) -> None:
    write_catalog(tmp_path, {"de": WITHOUT_PLAN_AND_NOTICE})
    model = model_answering(lambda english: f"DE {english}")

    main(["backend", "draft", "--language", "de"], tmp_path, factory(model))

    [request] = model.requests
    assert request.model_id == MODEL
    assert request.tools == []
    assert "into German" in str(request.system_prompt)
    assert "formally (Sie)" in str(request.system_prompt)
    assert asked_texts(request) == {
        "plans.chat.name": "Chat",
        "billing.notice": "{business}: pay {amount}.",
    }
    # A file of drafts is needs_review as a whole: no single draft keys.
    assert read_file(tmp_path, "de")["draft_keys"] == []


def test_a_draft_with_other_placeholders_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_catalog(tmp_path, {"ru": WITHOUT_PLAN_AND_NOTICE})
    model = model_answering(lambda english: english.replace("{amount}", "{sum}"))

    assert main(["backend", "draft", "--language", "ru"], tmp_path, factory(model)) == 1

    written = read_file(tmp_path, "ru")
    assert written["draft_keys"] == ["plans.chat.name"]
    assert "billing.notice" not in written["texts"]  # type: ignore[operator]
    assert "billing.notice: the draft was refused" in capsys.readouterr().out


@pytest.mark.parametrize(
    "answer",
    ["not json", '["a list"]', '```json\n{"plans.chat.name": ""}\n```'],
)
def test_an_unusable_answer_leaves_the_texts_missing(
    tmp_path: Path, answer: str
) -> None:
    write_catalog(tmp_path, {"ka": WITHOUT_PLAN_AND_NOTICE})
    model = ScriptedLlmAdapter.from_turns([ScriptedLlmTurn(text=MessageText(answer))])

    assert main(["backend", "draft", "--language", "ka"], tmp_path, factory(model)) == 1

    assert read_file(tmp_path, "ka")["draft_keys"] == []


def test_an_answer_in_a_code_fence_is_read(tmp_path: Path) -> None:
    write_catalog(tmp_path, {"ka": WITHOUT_PLAN_AND_NOTICE})
    fenced = (
        '```json\n{"plans.chat.name": "ჩატი", "billing.notice": '
        '"{business}: გადაიხადეთ {amount}."}\n```'
    )
    model = ScriptedLlmAdapter.from_turns([ScriptedLlmTurn(text=MessageText(fenced))])

    assert main(["backend", "draft", "--language", "ka"], tmp_path, factory(model)) == 0

    assert read_file(tmp_path, "ka")["texts"] == {
        **WITHOUT_PLAN_AND_NOTICE,
        "plans.chat.name": "ჩატი",
        "billing.notice": "{business}: გადაიხადეთ {amount}.",
    }


def test_a_new_language_without_a_file_starts_as_drafts(tmp_path: Path) -> None:
    write_catalog(tmp_path)
    (tmp_path / "he.json").unlink()
    model = model_answering(lambda english: f"HE {english}")

    assert main(["backend", "check"], tmp_path, never_called) == 1
    assert main(["backend", "draft", "--language", "he"], tmp_path, factory(model)) == 0

    written = read_file(tmp_path, "he")
    assert written["language"] == "he"
    assert written["review_status"] == "needs_review"
    assert len(written["texts"]) == len(ENGLISH_TEXTS)  # type: ignore[arg-type]


def test_nothing_missing_needs_no_model(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_catalog(tmp_path)

    assert main(["backend", "draft", "--language", "de"], tmp_path, never_called) == 0
    assert "de.json: nothing to draft" in capsys.readouterr().out


def test_reviewed_clears_named_drafts_or_the_whole_file(tmp_path: Path) -> None:
    write_catalog(tmp_path, {"ka": WITHOUT_PLAN_AND_NOTICE})
    model = model_answering(lambda english: f"KA {english}")
    main(["backend", "draft", "--language", "ka"], tmp_path, factory(model))

    reviewed = ["backend", "reviewed", "--language"]
    assert main([*reviewed, "ka", "--key", "billing.notice"], tmp_path) == 0
    assert read_file(tmp_path, "ka")["draft_keys"] == ["plans.chat.name"]

    assert main([*reviewed, "de"], tmp_path) == 0
    assert read_file(tmp_path, "de")["review_status"] == "reviewed"


def test_the_configured_drafter_uses_the_summary_model() -> None:
    container = AppContainer()
    replace_provider(
        container.config.app_settings,
        assemble_app_settings({"LLM_SUMMARY_MODEL_ID": "gpt-5-mini"}),
    )
    model = model_answering(lambda english: f"KA {english}")
    replace_provider(container.adapters.routing_llm_adapter, model)

    drafted = configured_drafter(container).draft(
        CabinetLanguage.GEORGIAN, {OwnerTextKey("plans.chat.name"): "Chat"}
    )

    assert drafted.drafts == {OwnerTextKey("plans.chat.name"): "KA Chat"}
    assert model.requests[0].model_id == "gpt-5-mini"
