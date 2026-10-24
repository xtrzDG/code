"""
A legal text owners accepted or read is never edited in place: the
fingerprints in docs/legal/published.json must match the files, a change
goes into a new dated version, and the release check counts the fields in
square brackets of the texts in force (failing only once LEGAL_TEXTS_FINAL
says they are final).
"""

import shutil
from pathlib import Path

import pytest

from app.registries.legal.legal_document_registry import (
    DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
)
from app.utilities.legal.legal_text_fingerprints import (
    count_placeholders,
    fingerprint,
)
from app.utilities.legal.subprocessor_table import TABLE_END_MARKER
from scripts import check_legal_texts, publish_legal_texts

TERMS: str = "terms-2026-10-05.en.md"
DPA: str = "dpa-2026-10-01.ru.md"


def published_copy(tmp_path: Path, *names: str) -> Path:
    for name in names:
        shutil.copy(DEFAULT_LEGAL_DOCUMENTS_DIRECTORY / name, tmp_path / name)
    assert publish_legal_texts.main([], tmp_path) == 0
    return tmp_path


def test_no_published_text_changed_in_place() -> None:
    changed, new, missing = publish_legal_texts.differences(
        DEFAULT_LEGAL_DOCUMENTS_DIRECTORY
    )

    assert changed == [], (
        "Published legal texts changed; keep them and add a new dated version: "
        f"{changed}"
    )
    assert missing == [], f"Published legal texts were removed: {missing}"
    assert new == [], (
        f"Record new versions: uv run python -m scripts.publish_legal_texts ({new})"
    )


def test_an_edited_text_is_refused_and_not_recorded(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = published_copy(tmp_path, TERMS)
    recorded = (directory / publish_legal_texts.MANIFEST_NAME).read_text()
    text = (directory / TERMS).read_text(encoding="utf-8")
    (directory / TERMS).write_text(text.replace("2026", "2027", 3), encoding="utf-8")

    assert publish_legal_texts.main(["--check"], directory) == 1
    assert publish_legal_texts.main([], directory) == 1
    assert (directory / publish_legal_texts.MANIFEST_NAME).read_text() == recorded
    assert "new dated version" in capsys.readouterr().out


def test_a_new_version_is_recorded_beside_the_old_one(tmp_path: Path) -> None:
    directory = published_copy(tmp_path, TERMS)
    shutil.copy(directory / TERMS, directory / "terms-2027-01-01.en.md")

    assert publish_legal_texts.main(["--check"], directory) == 1
    assert publish_legal_texts.main([], directory) == 0
    assert publish_legal_texts.differences(directory) == ([], [], [])
    assert sorted(publish_legal_texts.read_manifest(directory)) == [
        TERMS,
        "terms-2027-01-01.en.md",
    ]


def test_a_removed_text_is_reported(tmp_path: Path) -> None:
    directory = published_copy(tmp_path, TERMS)
    (directory / TERMS).unlink()

    assert publish_legal_texts.differences(directory) == ([], [], [TERMS])
    assert publish_legal_texts.main([], directory) == 1


def test_the_live_sub_processor_table_is_not_part_of_the_text() -> None:
    text = (DEFAULT_LEGAL_DOCUMENTS_DIRECTORY / DPA).read_text(encoding="utf-8")
    other_table = text.replace(
        TABLE_END_MARKER, f"| New | row | here | EU |\n{TABLE_END_MARKER}", 1
    )
    other_clause = text.replace("1.1.", "1.1. Changed.", 1)

    assert fingerprint(other_table) == fingerprint(text)
    assert fingerprint(other_clause) != fingerprint(text)


def test_placeholders_are_fields_not_links() -> None:
    text = "[Legal name], see [the policy](https://example.com) and [30] days."

    assert count_placeholders(text) == 2


def test_the_texts_in_force_are_the_dpa_version_and_the_latest_others(
    tmp_path: Path,
) -> None:
    for name in (
        "dpa-2026-10-01.en.md",
        "dpa-2026-10-06.en.md",
        "terms-2026-10-05.en.md",
        "terms-2027-01-01.en.md",
        "privacy-2026-10-05.en.md",
    ):
        (tmp_path / name).write_text("# Text\n", encoding="utf-8")

    chosen = check_legal_texts.texts_in_force(tmp_path, "2026-10-06", "2026-12-01")

    assert [path.name for path in chosen] == [
        "dpa-2026-10-06.en.md",
        "privacy-2026-10-05.en.md",
        "terms-2026-10-05.en.md",
    ]


def write_dpa(tmp_path: Path, text: str) -> Path:
    (tmp_path / "dpa-2026-10-06.en.md").write_text(text, encoding="utf-8")
    return tmp_path


def test_drafts_pass_the_release_check_with_their_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = write_dpa(tmp_path, "# DPA\n\n[Operator], [address].\n")

    status = check_legal_texts.main(
        {"DPA_DOCUMENT_VERSION": "2026-10-06"}, directory, "2026-10-06"
    )

    assert status == 0
    assert "2 field(s)" in capsys.readouterr().out


def test_final_texts_with_open_fields_fail_the_release_check(tmp_path: Path) -> None:
    directory = write_dpa(tmp_path, "# DPA\n\n[Operator].\n")
    environment = {"DPA_DOCUMENT_VERSION": "2026-10-06", "LEGAL_TEXTS_FINAL": "true"}

    assert check_legal_texts.main(environment, directory, "2026-10-06") == 1


def test_final_texts_without_open_fields_pass(tmp_path: Path) -> None:
    directory = write_dpa(tmp_path, "# DPA\n\nAssistant Workshop LLC, Tbilisi.\n")
    environment = {"DPA_DOCUMENT_VERSION": "2026-10-06", "LEGAL_TEXTS_FINAL": "yes"}

    assert check_legal_texts.main(environment, directory, "2026-10-06") == 0


def test_the_shipped_texts_are_drafts_with_open_fields() -> None:
    assert check_legal_texts.main({}) == 0
    assert check_legal_texts.main({"LEGAL_TEXTS_FINAL": "true"}) == 1
