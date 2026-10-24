"""
The Audit tab names every entity the backend writes in the reader's
language: each `AuditEntityName("…")` of the application, the kinds a
retention purge counts and the copies at each sub-processor have a label in
the cabinet's en, ru and ka dictionaries (a dotted name reads as one key
with underscores, as `auditEntityKey` in the cabinet looks it up).
"""

import re
from pathlib import Path

import pytest

from app.schemas.constants.privacy import SubProcessor
from app.use_cases.compliance.erase_processor_copies_use_case import (
    COPIES_ENTITY_SUFFIX,
)
from app.use_cases.compliance.retention.retention_audit import PURGED_ENTITIES

ROOT: Path = Path(__file__).resolve().parents[2]
DICTIONARIES: Path = ROOT / "web/src/i18n/messages/sections/workspace"
ENTITY_LITERAL: re.Pattern[str] = re.compile(r'AuditEntityName\(\s*"([a-z_.]+)"')
ENTITIES_BLOCK: re.Pattern[str] = re.compile(
    r"\n    entities: \{\n(.*?)\n    \},", re.S
)
LABEL_KEY: re.Pattern[str] = re.compile(r"^      ([a-z_]+): ", re.M)


def written_entities() -> set[str]:
    names: set[str] = set()
    for source in (ROOT / "app").rglob("*.py"):
        names.update(ENTITY_LITERAL.findall(source.read_text(encoding="utf-8")))
    names.update(entity for entity, _ in PURGED_ENTITIES)
    names.update(
        f"{processor.value}{COPIES_ENTITY_SUFFIX}" for processor in SubProcessor
    )
    return {name.replace(".", "_") for name in names}


def labelled_entities(language: str) -> set[str]:
    text = (DICTIONARIES / f"settingsRecords.{language}.ts").read_text(encoding="utf-8")
    block = ENTITIES_BLOCK.search(text)
    assert block is not None, f"settingsRecords.{language}.ts has no entities"
    return set(LABEL_KEY.findall(block.group(1)))


def test_the_backend_writes_the_entities_the_tab_knows() -> None:
    assert {"booking", "business_export", "export_download_link", "messages"} <= (
        written_entities()
    )


@pytest.mark.parametrize("language", ["en", "ru", "ka"])
def test_every_audit_entity_has_a_label(language: str) -> None:
    missing = sorted(written_entities() - labelled_entities(language))

    assert missing == [], (
        f"Add these to `settings.audit.entities` in settingsRecords.{language}.ts"
    )
