"""
Drafts of legal texts in the newer cabinet languages (docs/legal/drafts):
marked needs_review, numbered like the English text they translate, with
the generated sections' markers, and never served or accepted.
"""

import re
from pathlib import Path

import pytest

from app.registries.legal.legal_document_registry import (
    DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
    LegalDocumentRegistry,
)
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.localization.constrained_strings import LanguageTag

DRAFTS_DIRECTORY: Path = DEFAULT_LEGAL_DOCUMENTS_DIRECTORY / "drafts"
DRAFT_FILE: re.Pattern[str] = re.compile(
    r"^(?P<document>[a-z]+-[0-9]{4}-[0-9]{2}-[0-9]{2})\.(?P<language>[a-z]{2})\.md$"
)
SECTION: re.Pattern[str] = re.compile(r"^## (?P<number>[0-9]+)\. ", re.MULTILINE)
CLAUSE: re.Pattern[str] = re.compile(r"^(?P<number>[0-9]+\.[0-9]+)\. ", re.MULTILINE)
GENERATED_MARKERS: tuple[str, ...] = (
    "<!-- subprocessors:start",
    "<!-- subprocessors:end -->",
    "<!-- security-measures:start",
    "<!-- security-measures:end -->",
)
DRAFTS: list[Path] = sorted(
    path for path in DRAFTS_DIRECTORY.glob("*.md") if DRAFT_FILE.match(path.name)
)


def english_of(draft: Path) -> Path:
    match = DRAFT_FILE.match(draft.name)
    assert match is not None
    return DEFAULT_LEGAL_DOCUMENTS_DIRECTORY / f"{match.group('document')}.en.md"


def test_hebrew_and_german_dpa_drafts_exist() -> None:
    assert [path.name for path in DRAFTS] == [
        "dpa-2026-10-06.de.md",
        "dpa-2026-10-06.he.md",
    ]


@pytest.mark.parametrize("draft", DRAFTS, ids=lambda path: path.name)
def test_a_draft_is_marked_and_numbered_like_its_english_text(draft: Path) -> None:
    text: str = draft.read_text(encoding="utf-8")
    english: str = english_of(draft).read_text(encoding="utf-8")

    assert "needs_review" in "\n".join(text.splitlines()[:6])
    assert SECTION.findall(text) == SECTION.findall(english)
    assert CLAUSE.findall(text) == CLAUSE.findall(english)
    for marker in GENERATED_MARKERS:
        assert marker in text, marker


@pytest.mark.parametrize("language", ["he", "de"])
def test_a_draft_is_not_served(language: str) -> None:
    view = LegalDocumentRegistry().find_dpa(
        DpaDocumentVersion("2026-10-06"), LanguageTag(language)
    )

    assert view is not None
    assert str(view.language) == "en"
