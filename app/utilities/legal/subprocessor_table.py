"""
The DPA's section 8 table, rendered from the sub-processor registry.

The DPA files keep a generated copy between two markers, so the Markdown
reads well on its own (`scripts/render_subprocessor_table.py` writes it,
tests/legal checks it matches); the API serves the live rendering in the
markers' place.
"""

import re
from datetime import date, timedelta

from app.schemas.dto.legal import SubprocessorEntry
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.legal.constrained_strings import SubprocessorChangeDate
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import base_language_code
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver

TABLE_START_MARKER: str = (
    "<!-- subprocessors:start (generated from app/registries/legal; "
    "uv run python -m scripts.render_subprocessor_table) -->"
)
TABLE_END_MARKER: str = "<!-- subprocessors:end -->"
TABLE_BLOCK: re.Pattern[str] = re.compile(
    r"<!-- subprocessors:start[^\n]*-->\n(?P<table>.*?)\n<!-- subprocessors:end -->",
    re.DOTALL,
)

HEADERS: dict[str, tuple[str, str, str, str]] = {
    "en": ("Sub-processor", "Purpose", "Personal data", "Location"),
    "ru": ("Субобработчик", "Цель", "Персональные данные", "Где"),
    "ka": (
        "ქვე-უფლებამოსილი პირი",
        "მიზანი",
        "პერსონალური მონაცემები",
        "ადგილმდებარეობა",
    ),
}
# "(from 2026-12-01)": an announced addition; "(until ...)": its last day.
FROM_LABEL: dict[str, str] = {"en": "from {day}", "ru": "с {day}", "ka": "{day}-დან"}
UNTIL_LABEL: dict[str, str] = {
    "en": "until {day}",
    "ru": "по {day}",
    "ka": "{day}-მდე",
}
FALLBACK_LANGUAGE: str = "en"
_RESOLVER: LocalizedTextResolver = LocalizedTextResolver()


def table_language(language: LanguageTag) -> LanguageTag:
    """The language the list is written in for a request: en, ru or ka."""

    base: str = base_language_code(language)
    return LanguageTag(base if base in HEADERS else FALLBACK_LANGUAGE)


def render_subprocessor_table(
    entries: list[SubprocessorEntry], language: LanguageTag
) -> str:
    """The Markdown table in a language (the header in en, ru or ka)."""

    written_in: str = str(table_language(language))
    header: tuple[str, str, str, str] = HEADERS[written_in]
    lines: list[str] = [
        f"| {' | '.join(header)} |",
        f"| {' | '.join('---' for _ in header)} |",
    ]
    for entry in entries:
        cells: list[str] = [
            name_cell(entry, language, written_in),
            cell(entry.purpose, language),
            cell(entry.personal_data, language),
            cell(entry.location, language),
        ]
        lines.append(f"| {' | '.join(cells)} |")

    return "\n".join(lines)


def name_cell(entry: SubprocessorEntry, language: LanguageTag, written_in: str) -> str:
    """The name, with "(from ...)" or "(until ...)" for an announced change."""

    name: str = cell(entry.name, language)
    notes: list[str] = []
    if entry.addition_announced_on is not None:
        notes.append(FROM_LABEL[written_in].format(day=entry.added_on))
    if entry.removed_on is not None:
        notes.append(UNTIL_LABEL[written_in].format(day=last_day(entry.removed_on)))

    return f"{name} ({', '.join(notes)})" if notes else name


def last_day(removed_on: SubprocessorChangeDate) -> str:
    return (date.fromisoformat(str(removed_on)) - timedelta(days=1)).isoformat()


def cell(text: LocalizedText, language: LanguageTag) -> str:
    """A table cell: one line, no pipe that would split it."""

    value: str = str(_RESOLVER.resolve(text, language))
    return " ".join(value.split()).replace("|", "/")


def find_table_block(markdown: str) -> str | None:
    """The generated table between the markers, None without markers."""

    match: re.Match[str] | None = TABLE_BLOCK.search(markdown)
    return None if match is None else match.group("table")


def write_table_block(markdown: str, table: str) -> str:
    """The Markdown with the table between the markers replaced (kept markers)."""

    replacement: str = f"{TABLE_START_MARKER}\n{table}\n{TABLE_END_MARKER}"
    return TABLE_BLOCK.sub(lambda _match: replacement, markdown, count=1)


def serve_table_block(markdown: str, table: str) -> str:
    """The Markdown as served: the live table in place of the whole block."""

    return TABLE_BLOCK.sub(lambda _match: table, markdown, count=1)
