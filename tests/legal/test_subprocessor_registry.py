"""
The sub-processor registry is the single source of the DPA's section 8:
every translation's table is the registry's rendering, the served agreement
shows the live list, and a list that would break the DPA's 30-day promise
cannot be built.
"""

import re
from pathlib import Path

import pytest

from app.registries.legal.legal_document_registry import (
    DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
    DPA_FILE_PATTERN,
    LegalDocumentRegistry,
)
from app.registries.legal.subprocessor_catalog import SUBPROCESSORS
from app.registries.legal.subprocessor_registry import SubprocessorRegistry
from app.registries.legal.subprocessor_texts import texts
from app.schemas.constants.legal import SubprocessorChangeKind
from app.schemas.dto.legal import SubprocessorEntry
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.legal.constrained_integers import SubprocessorNoticeDays
from app.schemas.typings.legal.constrained_strings import SubprocessorChangeDate
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.legal.subprocessor_table import (
    TABLE_END_MARKER,
    find_table_block,
    render_subprocessor_table,
    write_table_block,
)
from app.utilities.localization.language_tags import parse_language_tag
from scripts.render_subprocessor_table import render_files
from tests.legal.legal_world import announced_entry, retiring_entry

DPA_FILES: list[Path] = sorted(DEFAULT_LEGAL_DOCUMENTS_DIRECTORY.glob("dpa-*.md"))


@pytest.mark.parametrize("path", DPA_FILES, ids=lambda path: path.name)
def test_every_dpa_translation_shows_the_registry_table(path: Path) -> None:
    match = DPA_FILE_PATTERN.match(path.name)
    assert match is not None
    block = find_table_block(path.read_text(encoding="utf-8"))

    assert block is not None, f"{path.name} has no generated sub-processor table"
    assert block == render_subprocessor_table(
        list(SUBPROCESSORS), parse_language_tag(match.group("language"))
    ), "Run: uv run python -m scripts.render_subprocessor_table"


def test_the_render_script_finds_nothing_stale() -> None:
    assert render_files(DEFAULT_LEGAL_DOCUMENTS_DIRECTORY, write=False) == []


def test_the_render_script_rewrites_only_the_table(tmp_path: Path) -> None:
    original = (DPA_FILES[0]).read_text(encoding="utf-8")
    stale = original.replace("| Render |", "| Hosting |", 1)
    (tmp_path / DPA_FILES[0].name).write_text(stale, encoding="utf-8")

    assert render_files(tmp_path, write=True) == [tmp_path / DPA_FILES[0].name]
    assert (tmp_path / DPA_FILES[0].name).read_text(encoding="utf-8") == original


def test_the_served_agreement_shows_the_live_list_without_markers() -> None:
    added = announced_entry("mailbox", added_on="2026-12-01", announced_on="2026-10-20")
    registry = LegalDocumentRegistry(
        subprocessor_registry=SubprocessorRegistry(entries=(*SUBPROCESSORS, added))
    )

    russian = registry.find_dpa(DpaDocumentVersion("2026-10-01"), LanguageTag("ru"))

    assert russian is not None
    assert "subprocessors:start" not in russian.text
    assert TABLE_END_MARKER not in russian.text
    assert "| Почта ЕС (с 2026-12-01) | Отправка писем |" in russian.text
    assert "| Субобработчик | Цель | Персональные данные | Где |" in russian.text


def test_announced_changes_are_marked_in_every_language() -> None:
    entries = [
        announced_entry("mailbox", added_on="2026-12-01", announced_on="2026-10-20"),
        retiring_entry(removed_on="2027-01-01", announced_on="2026-11-15"),
    ]

    english = render_subprocessor_table(entries, LanguageTag("en"))
    georgian = render_subprocessor_table(entries, LanguageTag("ka"))
    german = render_subprocessor_table(entries, LanguageTag("de"))

    assert "Mailbox EU (from 2026-12-01)" in english
    assert "(until 2026-12-31)" in english
    assert "ფოსტა ევროკავშირი (2026-12-01-დან)" in georgian
    assert "(2026-12-31-მდე)" in georgian
    # Languages without a DPA read the English table.
    assert german == english


def test_a_cell_never_splits_the_table() -> None:
    entry = announced_entry("pipes", added_on="2026-12-01", announced_on="2026-10-20")
    piped = entry.model_copy(
        update={"purpose": texts("Mail | delivery\nacross lines", "-", "-")}
    )

    row = render_subprocessor_table([piped], LanguageTag("en")).splitlines()[-1]

    assert row.count("|") == 5
    assert "Mail / delivery across lines" in row


def test_changes_are_derived_from_the_entries_earliest_first() -> None:
    registry = SubprocessorRegistry(
        entries=(
            retiring_entry(removed_on="2027-01-01", announced_on="2026-11-15"),
            *SUBPROCESSORS[1:],
            announced_entry(
                "mailbox", added_on="2026-12-01", announced_on="2026-10-20"
            ),
        )
    )

    changes = registry.list_changes()

    assert [(str(change.key), change.kind) for change in changes] == [
        ("mailbox-added-2026-12-01", SubprocessorChangeKind.ADDED),
        ("openai-removed-2027-01-01", SubprocessorChangeKind.REMOVED),
    ]
    assert str(changes[0].announced_on) == "2026-10-20"


def test_the_shipped_list_announces_its_changes_in_time() -> None:
    registry = SubprocessorRegistry()

    assert int(registry.notice_days()) == 30
    assert [str(entry.key) for entry in registry.list_entries()][:3] == [
        "openai",
        "elevenlabs",
        "zadarma",
    ]
    for change in registry.list_changes():
        assert str(change.effective_on) > str(change.announced_on)


@pytest.mark.parametrize(
    ("entries", "message"),
    [
        (
            (announced_entry("mailbox", "2026-12-01", announced_on="2026-11-15"),),
            "announced 16 days ahead; the DPA promises 30",
        ),
        (
            (retiring_entry(removed_on="2026-12-01", announced_on="2026-11-20"),),
            "announced 11 days ahead",
        ),
        (
            (
                announced_entry(
                    "mailbox", "2026-12-01", "2026-10-01", removed_on="2026-11-01"
                ),
            ),
            "removed before it was added",
        ),
        (
            (SUBPROCESSORS[0], SUBPROCESSORS[0]),
            "listed twice",
        ),
    ],
)
def test_a_list_that_breaks_the_promise_cannot_be_built(
    entries: tuple[SubprocessorEntry, ...], message: str
) -> None:
    with pytest.raises(ValueError, match=re.escape(message)):
        SubprocessorRegistry(entries=entries)


def test_a_removal_must_be_announced() -> None:
    unannounced = SUBPROCESSORS[0].model_copy(
        update={"removed_on": SubprocessorChangeDate("2027-01-01")}
    )

    with pytest.raises(ValueError, match="a removal must be announced"):
        SubprocessorRegistry(entries=(unannounced,))


def test_a_shorter_notice_period_is_its_own_promise() -> None:
    short = announced_entry("mailbox", "2026-12-01", announced_on="2026-11-15")

    registry = SubprocessorRegistry(
        entries=(short,), notice_days=SubprocessorNoticeDays(14)
    )

    assert len(registry.list_changes()) == 1


def test_a_file_without_markers_is_left_alone(tmp_path: Path) -> None:
    text = "# DPA\n\n## 8. Sub-processors\n\n| A | B |\n"

    assert write_table_block(text, "| x |") == text
    (tmp_path / "dpa-2020-01-01.en.md").write_text(text, encoding="utf-8")
    assert render_files(tmp_path, write=True) == []
