"""
Every sub-processor's transfer mechanism is published (DPA section 8 and
GET /v1/legal/subprocessors, PRIV-02) and agrees with the vendor register:
its "Location and safeguard" and DPA cells name each mechanism the registry
lists and no other, the transfer register dates each mechanism within a
year (PRIV-05), and production's backups are restored on a
GitHub-hosted runner only when that is switched on (GitHub is no
sub-processor).
"""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from pydantic import ValidationError

from app.registries.legal.subprocessor_registry import SubprocessorRegistry
from app.schemas.constants.legal import TransferMechanism
from app.schemas.dto.legal import SubprocessorEntry
from tests.legal.governance_documents import REPOSITORY, read, section, table_rows
from tests.legal.legal_world import announced_entry

RESTORE_DRILL: Path = REPOSITORY / ".github" / "workflows" / "restore-drill.yml"
LONGEST_GAP: timedelta = timedelta(days=366)
# How the vendor register words each mechanism.
REGISTER_WORDS: dict[TransferMechanism, tuple[str, ...]] = {
    TransferMechanism.EEA_PROCESSING: ("EU", "Frankfurt"),
    TransferMechanism.DATA_PRIVACY_FRAMEWORK: ("DPF",),
    TransferMechanism.STANDARD_CONTRACTUAL_CLAUSES: ("SCCs",),
    TransferMechanism.BINDING_CORPORATE_RULES: ("Binding Corporate Rules",),
    TransferMechanism.NONE_OFFERED: ("no safeguard", "under each vendor's terms"),
    TransferMechanism.TO_BE_CONFIRMED: ("to confirm",),
}
# Mechanisms a register row names only when the registry lists them.
EXPLICIT: tuple[TransferMechanism, ...] = (
    TransferMechanism.DATA_PRIVACY_FRAMEWORK,
    TransferMechanism.STANDARD_CONTRACTUAL_CLAUSES,
    TransferMechanism.BINDING_CORPORATE_RULES,
)
# The register's row of each sub-processor of app/registries/legal/.
REGISTER_ROW_OF: dict[str, str] = {
    "openai": "OpenAI",
    "openai_knowledge_search": "OpenAI",
    "elevenlabs": "ElevenLabs",
    "zadarma": "Zadarma",
    "meta": "Meta",
    "telegram": "Telegram",
    "flitt": "Flitt",
    "stripe": "Stripe",
    "langfuse": "Langfuse",
    "sentry": "Sentry",
    "render": "Render",
    "google_calendar": "Google",
    "anthropic": "Anthropic",
    "anthropic_quality_review": "Anthropic",
    "cloudflare_turnstile": "Cloudflare",
    "object_storage": "Object storage",
    "email": "E-mail provider",
    "twilio": "Twilio",
    "web_push": "Web push services",
}


def register() -> dict[str, str]:
    """Each vendor's location, safeguard and DPA cells as one text."""

    rows = table_rows(section(read("docs/operations/vendor-register.md"), "Register"))
    return {row[0].split(" (")[0]: f"{row[3]} {row[4]}" for row in rows}


def transfer_register() -> dict[str, list[str]]:
    text = section(read("docs/operations/vendor-register.md"), "Transfer register")
    return {row[0].split(" (")[0]: row for row in table_rows(text)}


def entries() -> list[SubprocessorEntry]:
    return SubprocessorRegistry().list_entries()


def test_every_sub_processor_names_its_transfer_mechanism() -> None:
    assert {str(entry.key) for entry in entries()} == set(REGISTER_ROW_OF)
    assert all(entry.transfer_mechanisms for entry in entries())
    entry = announced_entry("mailbox", "2026-12-01", "2026-10-20")
    with pytest.raises(ValidationError, match="transfer_mechanisms"):
        SubprocessorEntry.model_validate(
            entry.model_dump() | {"transfer_mechanisms": []}
        )


def test_the_registry_and_the_vendor_register_name_the_same_mechanisms() -> None:
    cells = register()

    for entry in entries():
        cell = cells[REGISTER_ROW_OF[str(entry.key)]]
        for mechanism in entry.transfer_mechanisms:
            words = REGISTER_WORDS[mechanism]
            assert any(word in cell for word in words), (entry.key, mechanism)
        for mechanism in EXPLICIT:
            if any(word in cell for word in REGISTER_WORDS[mechanism]):
                assert mechanism in entry.transfer_mechanisms, (entry.key, mechanism)


def test_a_transfer_outside_the_eea_has_a_row_in_the_transfer_register() -> None:
    rows = transfer_register()
    outside = {
        REGISTER_ROW_OF[str(entry.key)]
        for entry in entries()
        if entry.transfer_mechanisms != [TransferMechanism.EEA_PROCESSING]
    }

    assert sorted(outside - set(rows)) == []


def test_every_transfer_was_recorded_within_a_year() -> None:
    today = datetime.now(UTC).date()

    for vendor, row in transfer_register().items():
        recorded = date.fromisoformat(row[2])
        assert recorded <= today, f"{vendor}: a record cannot be dated ahead"
        assert today - recorded <= LONGEST_GAP, f"{vendor}: re-check the mechanism"
        # A DPF listing is proven by a dated screenshot of the official
        # list; SCCs alone need a transfer impact assessment.
        if "DPF" in row[1]:
            assert "DPF list screenshot" in row[3], vendor
        elif "SCCs" in row[1]:
            assert "TIA" in row[3], vendor


def test_github_hosted_runners_restore_no_production_backup_by_default() -> None:
    workflow = cast(dict[str, Any], yaml.safe_load(RESTORE_DRILL.read_text("utf-8")))
    jobs = cast(dict[str, dict[str, Any]], workflow["jobs"])
    production = jobs["production"]
    register = read("docs/operations/vendor-register.md")

    # The production job decrypts production's data on GitHub: a transfer
    # the DPA's list does not name, so it runs only when switched on.
    assert "vars.RESTORE_DRILL_ON_GITHUB == 'true'" in str(production["if"])
    assert production["environment"] == "backup-drill"
    assert all("GitHub" not in entry.name.model_dump_json() for entry in entries())
    assert "`RESTORE_DRILL_ON_GITHUB` unset" in register
    # The GitHub-hosted job of every night holds neither key nor bucket.
    hosted = str(jobs["round-trip"])
    assert "secrets." not in hosted
    assert "BACKUP_AGE_IDENTITY: ${{" not in hosted
