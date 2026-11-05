"""
Drafts of legal texts (docs/legal/drafts): translations into the other
cabinet language, and the next DPA version in English for the lawyer. Both
are marked needs_review, numbered like the English text in force, keep the
generated sections' markers, and are never served or accepted.
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
from app.utilities.config_helpers.app_settings.compliance_settings_section import (
    DEFAULT_DPA_DOCUMENT_VERSION,
)

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
    path
    for path in DRAFTS_DIRECTORY.glob("*.md")
    if DRAFT_FILE.match(path.name) and not path.name.endswith(".en.md")
)
# The next DPA version, drafted for the lawyer (PRIV-01): Article 28(3)(a)
# in clause 2.3 and the cabinet's closure in clause 13.3.
NEXT_DPA: Path = DRAFTS_DIRECTORY / "dpa-2026-11-03.en.md"


def english_of(draft: Path) -> Path:
    match = DRAFT_FILE.match(draft.name)
    assert match is not None
    return DEFAULT_LEGAL_DOCUMENTS_DIRECTORY / f"{match.group('document')}.en.md"


def test_the_italian_dpa_draft_exists() -> None:
    assert [path.name for path in DRAFTS] == ["dpa-2026-10-06.it.md"]


@pytest.mark.parametrize("draft", DRAFTS, ids=lambda path: path.name)
def test_a_draft_is_marked_and_numbered_like_its_english_text(draft: Path) -> None:
    text: str = draft.read_text(encoding="utf-8")
    english: str = english_of(draft).read_text(encoding="utf-8")

    assert "needs_review" in "\n".join(text.splitlines()[:6])
    assert SECTION.findall(text) == SECTION.findall(english)
    assert CLAUSE.findall(text) == CLAUSE.findall(english)
    for marker in GENERATED_MARKERS:
        assert marker in text, marker


@pytest.mark.parametrize("language", ["it", "it-IT"])
def test_a_draft_is_not_served(language: str) -> None:
    view = LegalDocumentRegistry().find_dpa(
        DpaDocumentVersion("2026-10-06"), LanguageTag(language)
    )

    assert view is not None
    assert str(view.language) == "en"


def clause(text: str, number: str) -> str:
    """The text of clause `number` up to the next clause or section."""

    match = re.search(
        rf"^{re.escape(number)}\. (.*?)(?=^[0-9]+\.[0-9]+\. |^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert match is not None, number
    return " ".join(match.group(1).split())


def test_the_next_dpa_version_is_a_draft_numbered_like_the_one_in_force() -> None:
    text: str = NEXT_DPA.read_text(encoding="utf-8")
    in_force: str = (
        DEFAULT_LEGAL_DOCUMENTS_DIRECTORY / f"dpa-{DEFAULT_DPA_DOCUMENT_VERSION}.en.md"
    ).read_text(encoding="utf-8")

    assert "needs_review" in "\n".join(text.splitlines()[:6])
    assert f"Changes from version {DEFAULT_DPA_DOCUMENT_VERSION}" in text
    assert NEXT_DPA.name.removeprefix("dpa-")[:10] > DEFAULT_DPA_DOCUMENT_VERSION
    assert SECTION.findall(text) == SECTION.findall(in_force)
    assert CLAUSE.findall(text) == CLAUSE.findall(in_force)
    for marker in GENERATED_MARKERS:
        assert marker in text, marker


def test_the_next_dpa_version_closes_the_annexs_gaps() -> None:
    text: str = NEXT_DPA.read_text(encoding="utf-8")

    # Article 28(3)(a): a legal requirement to process otherwise is told first.
    instructions = clause(text, "2.3")
    assert "Member State law" in instructions
    assert "informs the Client of that legal requirement before processing" in (
        instructions
    )
    # 13.3: the cabinet closes and deletes a business, with a certificate.
    end = clause(text, "13.3")
    assert "does not offer this yet" not in end
    assert "close the business in the cabinet" in end
    assert "deletion certificate" in end
    assert "the mechanism of each sub-processor" in clause(text, "7.2")


def test_the_next_dpa_version_is_not_served_or_published() -> None:
    published: str = (DEFAULT_LEGAL_DOCUMENTS_DIRECTORY / "published.json").read_text(
        encoding="utf-8"
    )

    assert NEXT_DPA.name not in published
    assert not (DEFAULT_LEGAL_DOCUMENTS_DIRECTORY / NEXT_DPA.name).exists()
    assert (
        LegalDocumentRegistry().find_dpa(
            DpaDocumentVersion(NEXT_DPA.name[4:14]), LanguageTag("en")
        )
        is None
    )
