"""Catalog lookups: texts, numbered lists, filled placeholders and the registry."""

from pathlib import Path

import pytest

from app.registries.localization.text_catalog_registry import TextCatalogRegistry
from app.schemas.constants.localization import CabinetLanguage, TextReviewStatus
from app.schemas.dto.text_catalog import TextCatalog
from app.schemas.typings.localization.constrained_strings import OwnerTextKey
from app.utilities.localization.owner_texts import (
    filled_owner_text,
    has_owner_text,
    owner_rule_lines,
    owner_text,
    owner_text_list,
)
from app.utilities.localization.text_catalog_files import (
    TextCatalogError,
    read_text_catalog,
)
from tests.localization.text_catalog.catalog_builders import (
    ENGLISH_TEXTS,
    write_catalog,
    write_catalog_file,
)


def small_catalog(tmp_path: Path) -> TextCatalog:
    write_catalog(
        tmp_path,
        {
            "ru": {
                "plans.chat.name": "Чат",
                "niches.cafe.handoff_rules.1": "Жалоба",
                "niches.cafe.handoff_rules.2": "Большая группа",
            },
            "de": {"plans.chat.name": "Chat", "niches.cafe.handoff_rules.1": "B"},
        },
    )
    write_catalog_file(
        tmp_path,
        "ka",
        {"plans.chat.name": "ჩატი", "billing.notice": "{business}: {amount}."},
        draft_keys=["billing.notice"],
    )
    return read_text_catalog(tmp_path)


def test_a_text_lists_english_first_then_every_language_that_has_it(
    tmp_path: Path,
) -> None:
    text = owner_text("plans.chat.name", small_catalog(tmp_path))

    assert [str(tag) for tag in text.values] == ["en", "ru", "ka", "he", "de"]
    assert text.values[next(iter(text.values))] == "Chat"


def test_an_unknown_key_fails_at_once(tmp_path: Path) -> None:
    with pytest.raises(TextCatalogError, match=r"en.json has no text plans.gone"):
        owner_text("plans.gone.name", small_catalog(tmp_path))

    assert has_owner_text("plans.chat.name", small_catalog(tmp_path))
    assert not has_owner_text("plans.gone.name", small_catalog(tmp_path))


def test_a_list_is_shown_only_in_languages_that_have_every_line(
    tmp_path: Path,
) -> None:
    rules = owner_rule_lines("niches.cafe.handoff_rules", small_catalog(tmp_path))

    assert {str(tag): str(value) for tag, value in rules.values.items()} == {
        "en": "Complaint\nLarge group",
        "ru": "Жалоба\nБольшая группа",
        "he": "Complaint\nLarge group",
    }
    with pytest.raises(TextCatalogError, match="no numbered texts"):
        owner_rule_lines("niches.bar.handoff_rules", small_catalog(tmp_path))


def test_numbered_texts_come_one_by_one(tmp_path: Path) -> None:
    lines = owner_text_list("niches.cafe.handoff_rules", small_catalog(tmp_path))

    assert [str(line.values[next(iter(line.values))]) for line in lines] == [
        "Complaint",
        "Large group",
    ]
    with pytest.raises(TextCatalogError, match="no numbered texts"):
        owner_text_list("forwarding.steps", small_catalog(tmp_path))


def test_a_filled_text_keeps_the_placeholders_it_was_not_given(
    tmp_path: Path,
) -> None:
    text = filled_owner_text(
        "billing.notice", small_catalog(tmp_path), business="Mtsvane"
    )

    assert {str(tag): str(value) for tag, value in text.values.items()} == {
        "en": "Mtsvane: pay {amount}.",
        "ka": "Mtsvane: {amount}.",
        "he": "Mtsvane: pay {amount}.",
    }


def test_the_registry_reports_missing_texts_and_review_status(tmp_path: Path) -> None:
    registry = TextCatalogRegistry(small_catalog(tmp_path))
    chat, notice = OwnerTextKey("plans.chat.name"), OwnerTextKey("billing.notice")

    assert registry.list_keys() == [OwnerTextKey(key) for key in ENGLISH_TEXTS]
    assert (
        registry.get(chat).values
        == owner_text("plans.chat.name", small_catalog(tmp_path)).values
    )
    assert registry.list_missing_keys(CabinetLanguage.GEORGIAN) == [
        OwnerTextKey("niches.cafe.handoff_rules.1"),
        OwnerTextKey("niches.cafe.handoff_rules.2"),
    ]
    assert registry.review_status(chat, CabinetLanguage.GEORGIAN) is (
        TextReviewStatus.REVIEWED
    )
    assert registry.review_status(notice, CabinetLanguage.GEORGIAN) is (
        TextReviewStatus.NEEDS_REVIEW
    )
    assert registry.review_status(chat, CabinetLanguage.HEBREW) is (
        TextReviewStatus.NEEDS_REVIEW
    )
    assert registry.review_status(notice, CabinetLanguage.RUSSIAN) is None


def test_the_default_registry_serves_the_shipped_catalog() -> None:
    registry = TextCatalogRegistry()

    assert registry.list_missing_keys(CabinetLanguage.HEBREW) == []
    assert registry.get(OwnerTextKey("plans.plus.name")).values
