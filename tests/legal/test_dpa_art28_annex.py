"""
The Article 28(3) annex (docs/legal/drafts/dpa-art28-annex.md) maps the DPA
in force: every duty (a) to (h) has a row, every clause it cites exists in
that DPA version, every code and test path exists, and the annex stays a
draft the API never serves.
"""

import re

from app.registries.legal.legal_document_registry import (
    DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
    DPA_FILE_PATTERN,
)
from app.utilities.config_helpers.app_settings.compliance_settings_section import (
    DEFAULT_DPA_DOCUMENT_VERSION,
)
from tests.legal.governance_documents import (
    OPERATIONS,
    missing_paths,
    section,
    table_rows,
)

ANNEX = DEFAULT_LEGAL_DOCUMENTS_DIRECTORY / "drafts" / "dpa-art28-annex.md"
DUTIES: tuple[str, ...] = tuple(f"({letter})" for letter in "abcdefgh")
CLAUSE: re.Pattern[str] = re.compile(r"^(?P<number>[0-9]+\.[0-9]+)\. ", re.MULTILINE)
CITED: re.Pattern[str] = re.compile(r"\b[0-9]+\.[0-9]+\b")


def annex_text() -> str:
    return ANNEX.read_text(encoding="utf-8")


def dpa_clauses() -> set[str]:
    dpa = (
        DEFAULT_LEGAL_DOCUMENTS_DIRECTORY / f"dpa-{DEFAULT_DPA_DOCUMENT_VERSION}.en.md"
    )
    return set(CLAUSE.findall(dpa.read_text(encoding="utf-8")))


def test_the_annex_maps_the_dpa_version_in_force() -> None:
    assert f"`docs/legal/dpa-{DEFAULT_DPA_DOCUMENT_VERSION}.en.md`" in annex_text()


def test_every_duty_of_article_28_3_has_a_row_with_its_clauses() -> None:
    rows = table_rows(section(annex_text(), "Duties of Article 28(3)"))
    duties = {row[0].split(",")[0] for row in rows}

    assert set(DUTIES) <= duties
    for row in rows:
        assert len(row) == 5 and all(row), row
        assert CITED.findall(row[2]), row


def test_every_cited_clause_exists_in_the_dpa() -> None:
    text = annex_text()
    cited = {
        clause
        for heading in ("Duties of Article 28(3)", "Other paragraphs of Article 28")
        for row in table_rows(section(text, heading))
        for clause in CITED.findall(row[2] if len(row) == 5 else row[1])
    }

    assert len(cited) >= 15
    assert sorted(cited - dpa_clauses()) == []


def test_the_annex_names_only_paths_that_exist() -> None:
    assert missing_paths(annex_text(), OPERATIONS) == []


def test_the_annex_is_a_draft_the_api_does_not_serve() -> None:
    assert "needs_review" in "\n".join(annex_text().splitlines()[:4])
    assert DPA_FILE_PATTERN.match(ANNEX.name) is None
    assert ANNEX.parent.name == "drafts"
