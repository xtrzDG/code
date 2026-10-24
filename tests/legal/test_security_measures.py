"""
DPA section 9 is generated from the security measure registry: every
measure names code that exists, every version from 2026-10-06 on carries the
list as the registry gives it for that version (in every language), and the
served agreement shows it as written, without its markers.
"""

import re
from pathlib import Path

import pytest

from app.registries.legal.legal_document_registry import (
    DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
    DPA_FILE_PATTERN,
    LegalDocumentRegistry,
)
from app.registries.legal.security_measure_registry import (
    SECURITY_MEASURES,
    SecurityMeasureRegistry,
)
from app.registries.legal.security_measures_access import GENERATED_SECTION_FROM
from app.registries.legal.subprocessor_texts import texts
from app.schemas.dto.security_measures import SecurityMeasure
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.legal.constrained_strings import (
    RepositoryPath,
    SecurityMeasureKey,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.config_helpers.app_settings.compliance_settings_section import (
    DEFAULT_DPA_DOCUMENT_VERSION,
)
from app.utilities.legal.security_measures_section import (
    SECTION_START_MARKER,
    find_security_block,
    render_security_measures,
    write_security_block,
)
from app.utilities.localization.language_tags import parse_language_tag
from scripts.render_subprocessor_table import render_files

REPOSITORY_ROOT: Path = DEFAULT_LEGAL_DOCUMENTS_DIRECTORY.parents[1]
DPA_FILES: list[Path] = sorted(DEFAULT_LEGAL_DOCUMENTS_DIRECTORY.glob("dpa-*.md"))


def file_version(path: Path) -> tuple[str, str]:
    match = DPA_FILE_PATTERN.match(path.name)
    assert match is not None
    return match.group("version"), match.group("language")


def measure(
    key: str, listed_from: str, listed_until: str | None = None
) -> SecurityMeasure:
    return SecurityMeasure(
        key=SecurityMeasureKey(key),
        text=texts(f"{key} in English", f"{key} по-русски", f"{key} ქართულად"),
        implemented_by=[RepositoryPath("app/main.py")],
        listed_from=DpaDocumentVersion(listed_from),
        listed_until=None if listed_until is None else DpaDocumentVersion(listed_until),
    )


@pytest.mark.parametrize(
    "path",
    sorted(
        {path for item in SECURITY_MEASURES for path in item.implemented_by}, key=str
    ),
    ids=str,
)
def test_every_measure_names_code_that_exists(path: RepositoryPath) -> None:
    assert (REPOSITORY_ROOT / str(path)).exists(), (
        f"{path} is named in DPA section 9 but is not in the repository"
    )


def test_every_measure_names_its_code() -> None:
    assert all(item.implemented_by for item in SECURITY_MEASURES)


def test_the_current_version_generates_its_section_9() -> None:
    current = [
        path
        for path in DPA_FILES
        if file_version(path)[0] == DEFAULT_DPA_DOCUMENT_VERSION
    ]

    assert {file_version(path)[1] for path in current} == {"en", "ru", "ka"}
    for path in current:
        assert SECTION_START_MARKER in path.read_text(encoding="utf-8"), path.name


@pytest.mark.parametrize("path", DPA_FILES, ids=lambda path: path.name)
def test_every_generated_section_is_the_registry_list(path: Path) -> None:
    version, language = file_version(path)
    block = find_security_block(path.read_text(encoding="utf-8"))
    if version < str(GENERATED_SECTION_FROM):
        assert block is None, "Versions before 2026-10-06 keep their own section 9"
        return

    measures = SecurityMeasureRegistry().measures_of(DpaDocumentVersion(version))
    assert block is not None, f"{path.name} has no generated section 9"
    assert block == render_security_measures(measures, parse_language_tag(language)), (
        "Run: uv run python -m scripts.render_subprocessor_table"
    )


def test_the_render_script_rewrites_a_stale_list(tmp_path: Path) -> None:
    current = (
        DEFAULT_LEGAL_DOCUMENTS_DIRECTORY / f"dpa-{DEFAULT_DPA_DOCUMENT_VERSION}.en.md"
    )
    original = current.read_text(encoding="utf-8")
    stale = write_security_block(original, "- an old list.")
    (tmp_path / current.name).write_text(stale, encoding="utf-8")

    assert render_files(tmp_path, write=False) == [tmp_path / current.name]
    assert render_files(tmp_path, write=True) == [tmp_path / current.name]
    assert (tmp_path / current.name).read_text(encoding="utf-8") == original


def test_the_served_agreement_shows_the_list_without_markers() -> None:
    registry = LegalDocumentRegistry()
    version = DpaDocumentVersion(DEFAULT_DPA_DOCUMENT_VERSION)

    georgian = registry.find_dpa(version, LanguageTag("ka"))

    assert georgian is not None
    assert "security-measures:" not in georgian.text
    first = SecurityMeasureRegistry().measures_of(version)[0]
    assert render_security_measures([first], LanguageTag("ka"))[2:-1] in georgian.text


def test_a_version_lists_the_measures_in_force_on_its_date() -> None:
    registry = SecurityMeasureRegistry(
        (
            measure("always", "2026-10-06"),
            measure("later", "2027-01-01"),
            measure("retired", "2026-10-06", listed_until="2027-01-01"),
        )
    )

    def keys(version: str) -> list[str]:
        return [
            str(item.key) for item in registry.measures_of(DpaDocumentVersion(version))
        ]

    assert keys("2026-10-01") == []
    assert keys("2026-10-06") == ["always", "retired"]
    assert keys("2027-01-01") == ["always", "later"]


def test_a_measure_cannot_be_listed_twice() -> None:
    with pytest.raises(ValueError, match="twice"):
        SecurityMeasureRegistry(
            (measure("audit", "2026-10-06"), measure("audit", "2027-01-01"))
        )


def test_the_list_reads_as_one_sentence() -> None:
    rendered = render_security_measures(
        [measure("first", "2026-10-06"), measure("second", "2026-10-06")],
        LanguageTag("ru"),
    )

    assert rendered.splitlines() == ["- first по-русски;", "- second по-русски."]


def test_a_path_must_stay_inside_the_repository() -> None:
    for unsafe in ("/etc/passwd", "app/../../secrets", "app/main.py; rm"):
        with pytest.raises(ValueError):
            RepositoryPath(unsafe)

    assert re.fullmatch(r"[a-z_/]+\.py", str(RepositoryPath("app/main.py")))
