"""
The DPA's section 9 list of security measures, rendered from the security
measure registry for one DPA version.

Unlike the sub-processor table (served live, DPA 8.3), the list is part of
the text an owner accepts: it is written into each version's files once
(`scripts/render_subprocessor_table.py`), tests/legal checks it matches the
registry for that version, and the API serves it as written, markers
removed.
"""

import re

from app.schemas.dto.security_measures import SecurityMeasure
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.legal.subprocessor_table import cell

SECTION_START_MARKER: str = (
    "<!-- security-measures:start (generated from app/registries/legal; "
    "uv run python -m scripts.render_subprocessor_table) -->"
)
SECTION_END_MARKER: str = "<!-- security-measures:end -->"
SECTION_BLOCK: re.Pattern[str] = re.compile(
    r"<!-- security-measures:start[^\n]*-->\n(?P<section>.*?)\n"
    r"<!-- security-measures:end -->",
    re.DOTALL,
)


def render_security_measures(
    measures: list[SecurityMeasure], language: LanguageTag
) -> str:
    """One Markdown bullet per measure: ";" between them, "." after the last."""

    lines: list[str] = []
    for index, measure in enumerate(measures):
        ending: str = "." if index == len(measures) - 1 else ";"
        lines.append(f"- {cell(measure.text, language)}{ending}")

    return "\n".join(lines)


def find_security_block(markdown: str) -> str | None:
    """The generated list between the markers, None without markers."""

    match: re.Match[str] | None = SECTION_BLOCK.search(markdown)
    return None if match is None else match.group("section")


def write_security_block(markdown: str, section: str) -> str:
    """The Markdown with the list between the markers replaced (kept markers)."""

    replacement: str = f"{SECTION_START_MARKER}\n{section}\n{SECTION_END_MARKER}"
    return SECTION_BLOCK.sub(lambda _match: replacement, markdown, count=1)


def strip_security_markers(markdown: str) -> str:
    """The Markdown as served: the list as written, without its markers."""

    return SECTION_BLOCK.sub(lambda match: match.group("section"), markdown, count=1)
