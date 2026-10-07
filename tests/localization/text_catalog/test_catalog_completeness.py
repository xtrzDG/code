"""
The shipped catalog: complete in every cabinet language, drafts marked,
no text nobody shows, and the same languages the cabinet offers.
"""

import re
from pathlib import Path

from app.registries.localization.text_catalog_registry import TextCatalogRegistry
from app.schemas.constants.localization import (
    CABINET_LANGUAGES,
    CabinetLanguage,
    TextReviewStatus,
)
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.knowledge.localized_texts import split_rule_lines
from app.utilities.localization.owner_texts import OWNER_TEXT_CATALOG
from tests.architecture_policy.owner_text_sources import owner_facing_texts

WEB_LOCALE_CONFIG: Path = (
    Path(__file__).resolve().parents[3] / "web" / "src" / "i18n" / "config.ts"
)
WEB_LIST_PATTERN: re.Pattern[str] = re.compile(
    r"export const (LOCALES|CABINET_LANGUAGES)\b[^=]*=\s*\[([^\]]*)\]"
)
# Texts the code fills before it shows them, so their English never appears
# as it is written in the catalog.
FILLED_TEMPLATES: frozenset[str] = frozenset({"forwarding.carrier_unconfirmed"})
DRAFT_LANGUAGES: frozenset[CabinetLanguage] = frozenset(
    {CabinetLanguage.HEBREW, CabinetLanguage.GERMAN}
)


def test_every_cabinet_language_has_every_text() -> None:
    registry = TextCatalogRegistry()

    missing: dict[str, list[str]] = {
        language.value: [str(key) for key in registry.list_missing_keys(language)]
        for language in CABINET_LANGUAGES
    }

    assert missing == {language.value: [] for language in CABINET_LANGUAGES}


def test_hebrew_and_german_are_drafts_and_the_rest_reviewed() -> None:
    statuses = {
        language: catalog_file.review_status
        for language, catalog_file in OWNER_TEXT_CATALOG.files.items()
    }

    assert {
        language
        for language, status in statuses.items()
        if status is TextReviewStatus.NEEDS_REVIEW
    } == DRAFT_LANGUAGES


def english_lines(texts: list[LocalizedText]) -> set[str]:
    """Every English text and every line of a multi-line text."""

    found: set[str] = set()
    for text in texts:
        english = text.values[LanguageTag("en")]
        found.add(str(english))
        found.update(split_rule_lines(english))

    return found


def test_every_catalog_text_is_shown_somewhere() -> None:
    shown: set[str] = english_lines(owner_facing_texts())
    english = OWNER_TEXT_CATALOG.files[CabinetLanguage.ENGLISH].texts

    unused: list[str] = [
        str(key)
        for key, value in english.items()
        if str(key) not in FILLED_TEMPLATES and str(value) not in shown
    ]

    assert unused == []


def web_language_lists() -> dict[str, set[str]]:
    source: str = WEB_LOCALE_CONFIG.read_text(encoding="utf-8")
    return {
        name: set(re.findall(r'"([a-z]{2,3})"', values))
        for name, values in WEB_LIST_PATTERN.findall(source)
    }


def test_the_backend_has_texts_for_every_language_the_cabinet_offers() -> None:
    lists: dict[str, set[str]] = web_language_lists()
    backend: set[str] = {language.value for language in CABINET_LANGUAGES}

    assert "LOCALES" in lists
    for name, languages in lists.items():
        assert languages <= backend, f"web {name} has {languages - backend}"
