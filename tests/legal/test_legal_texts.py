"""
The legal texts in docs/legal: every document in English, Russian and
Georgian with the same sections, its version in the file name and in the
text, and every field still in square brackets tracked as a launch blocker
in docs/LAUNCH.md until a lawyer has filled it.
"""

import re
from collections import defaultdict
from pathlib import Path

import pytest

from app.registries.legal.legal_document_registry import (
    DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
)
from app.registries.legal.legal_text_registry import PLACEHOLDER_PATTERN

LEGAL_FILE: re.Pattern[str] = re.compile(
    r"^(?P<document>[a-z]+-[0-9]{4}-[0-9]{2}-[0-9]{2})\.(?P<language>[a-z]{2})\.md$"
)
LANGUAGES: set[str] = {"en", "ru", "ka"}
LAUNCH_GUIDE: Path = DEFAULT_LEGAL_DOCUMENTS_DIRECTORY.parents[0] / "LAUNCH.md"


def legal_files() -> dict[str, dict[str, Path]]:
    documents: dict[str, dict[str, Path]] = defaultdict(dict)
    for path in sorted(DEFAULT_LEGAL_DOCUMENTS_DIRECTORY.glob("*.md")):
        match = LEGAL_FILE.match(path.name)
        if match is not None:
            documents[match.group("document")][match.group("language")] = path
    return documents


DOCUMENTS: dict[str, dict[str, Path]] = legal_files()


def test_terms_privacy_and_cookies_are_published() -> None:
    kinds = {name.rsplit("-", 3)[0] for name in DOCUMENTS}

    assert {"dpa", "terms", "privacy", "cookies"} <= kinds


@pytest.mark.parametrize("document", sorted(DOCUMENTS))
def test_every_document_has_the_same_sections_in_every_language(
    document: str,
) -> None:
    translations = DOCUMENTS[document]

    assert set(translations) == LANGUAGES
    shapes = {
        language: (
            len(re.findall(r"^## ", text, re.MULTILINE)),
            len(re.findall(r"^\|", text, re.MULTILINE)),
            len(re.findall(r"^- ", text, re.MULTILINE)),
        )
        for language, text in (
            (language, path.read_text(encoding="utf-8"))
            for language, path in translations.items()
        )
    }
    assert len(set(shapes.values())) == 1, shapes


@pytest.mark.parametrize(
    "path",
    [path for translations in DOCUMENTS.values() for path in translations.values()],
    ids=lambda path: path.name,
)
def test_every_text_names_its_version_under_its_title(path: Path) -> None:
    version = re.search(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", path.name)
    lines = path.read_text(encoding="utf-8").splitlines()

    assert version is not None
    assert lines[0].startswith("# ")
    assert version.group(0) in lines[2]


def test_every_text_with_open_fields_is_a_launch_blocker() -> None:
    guide = LAUNCH_GUIDE.read_text(encoding="utf-8")
    blockers = guide[guide.index("### Блокер запуска: юридические тексты") :]

    unfilled = sorted(
        document
        for document, translations in DOCUMENTS.items()
        if any(
            PLACEHOLDER_PATTERN.search(path.read_text(encoding="utf-8"))
            for path in translations.values()
        )
    )

    assert unfilled, "No open fields left: remove the blocker from docs/LAUNCH.md."
    missing = [document for document in unfilled if document not in blockers]
    assert missing == [], f"List these in the LAUNCH.md blocker: {missing}"
