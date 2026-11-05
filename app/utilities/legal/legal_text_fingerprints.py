"""
Fingerprints of published legal texts: a text owners accepted or read is
never edited in place. The fingerprint covers the whole file except the
generated sub-processor table (DPA 8.3: the list changes with notice and is
served live), so re-rendering the table keeps every version's fingerprint.
"""

import hashlib
import re

from app.utilities.legal.subprocessor_table import (
    TABLE_BLOCK,
    TABLE_END_MARKER,
    TABLE_START_MARKER,
)

# A published file under docs/legal: dpa-, terms-, privacy- or cookies-
# <date>.<language>.md (the README is documentation, not a legal text).
LEGAL_TEXT_NAME: re.Pattern[str] = re.compile(
    r"^(dpa|terms|privacy|cookies)-[0-9]{4}-[0-9]{2}-[0-9]{2}\.[a-z]{2,3}\.md$"
)
# "[Legal name of the operator]": a field to fill; "[text](url)" is a link
# (the same rule as the legal text registry's `has_placeholders`).
PLACEHOLDER: re.Pattern[str] = re.compile(r"\[[^\]\n]+\](?!\()")


def fingerprint(text: str) -> str:
    """SHA-256 of the text with the generated table emptied (markers kept)."""

    normalized: str = TABLE_BLOCK.sub(
        lambda _match: f"{TABLE_START_MARKER}\n\n{TABLE_END_MARKER}", text
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def count_placeholders(text: str) -> int:
    """Fields in square brackets still to be filled in (not Markdown links)."""

    return len(PLACEHOLDER.findall(text))
