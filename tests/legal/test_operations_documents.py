"""
The operations documents stay true and current: every path and link they
name exists, every runbook is in the index once, every sub-processor of the
registry is in the vendor register with an exit plan and a console the
offboarding removes, the register's yearly review and the yearly tabletop
are not overdue (nor dated ahead), the on-call hours are Italian time, and
every alert the product objectives name exists.
"""

import re
from collections import Counter
from datetime import UTC, date, datetime, timedelta

import pytest

from app.registries.legal.subprocessor_registry import SubprocessorRegistry
from tests.legal.governance_documents import (
    OPERATIONS,
    REPOSITORY,
    broken_links,
    missing_paths,
    read,
    section,
    table_rows,
)

RUNBOOKS = OPERATIONS / "runbooks"
DOCUMENTS: tuple[str, ...] = (
    "docs/operations/on-call.md",
    "docs/operations/contacts.md",
    "docs/operations/offboarding.md",
    "docs/operations/tabletop.md",
    "docs/operations/maintenance.md",
    "docs/operations/vendor-register.md",
    "docs/operations/dependency-map.md",
    "docs/operations/slo.md",
    "docs/operations/status-page.md",
    "docs/operations/runbooks/README.md",
    "docs/operations/runbooks/render-outage.md",
    "docs/operations/runbooks/dns-outage.md",
    "docs/operations/runbooks/sms-outage.md",
    "docs/operations/runbooks/email-outage.md",
    "docs/operations/runbooks/data-breach.md",
    "docs/operations/runbooks/secret-rotation.md",
    "docs/operations/runbooks/sms-pumping.md",
    "docs/security/README.md",
    "docs/security/change-risk.md",
    "docs/security/runtime-protections.md",
    "docs/security/product-protections.md",
)
# The register's name of each sub-processor of app/registries/legal/.
REGISTER_NAME_OF: dict[str, str] = {
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
# Browser infrastructure: no console of ours to remove anyone from.
WITHOUT_CONSOLE: frozenset[str] = frozenset({"Web push services"})
CRITICALITY: frozenset[str] = frozenset({"critical", "high", "medium", "low"})
LONGEST_GAP: timedelta = timedelta(days=366)
# A planned tabletop gets a month to be recorded once its day has passed.
OVERDUE_PLAN: timedelta = timedelta(days=31)
PLANNED: str = "(planned)"
ISO_DATE: re.Pattern[str] = re.compile(r"\b(20[0-9]{2}-[01][0-9]-[0-3][0-9])\b")
# The cabinet and the help center speak English and Italian; the languages
# of the first market before Italy are gone.
FORMER_LANGUAGES: re.Pattern[str] = re.compile(r"`(?:ru|ka)`|\b(?:Russian|Georgian)\b")
PRODUCT_OBJECTIVES: tuple[str, ...] = (
    "Calls answered",
    "Voice latency",
    "Booking success",
    "Notification delivery",
    "Webhook lag",
)


def short_name(cell: str) -> str:
    return cell.split(" (")[0].strip()


def register_rows() -> dict[str, list[str]]:
    rows = table_rows(section(read("docs/operations/vendor-register.md"), "Register"))
    return {short_name(row[0]): row for row in rows}


def today() -> date:
    return datetime.now(UTC).date()


@pytest.mark.parametrize("document", DOCUMENTS)
def test_every_path_and_link_of_the_documents_exists(document: str) -> None:
    path = REPOSITORY / document

    assert missing_paths(read(document), OPERATIONS, path.parent) == []
    assert broken_links(path) == []


def test_every_runbook_is_in_the_index_once() -> None:
    index = read("docs/operations/runbooks/README.md")
    runbooks = {path.name for path in RUNBOOKS.glob("*.md")} - {"README.md"}
    listed = Counter(re.findall(r"^\| \[[a-z-]+\]\(([a-z-]+\.md)\)", index, re.M))

    assert sorted(name for name in runbooks if f"]({name})" not in index) == []
    assert sorted(name for name, count in listed.items() if count > 1) == []


def test_every_sub_processor_is_in_the_vendor_register() -> None:
    keys = {str(entry.key) for entry in SubprocessorRegistry().list_entries()}
    register = register_rows()

    assert keys == set(REGISTER_NAME_OF), "map the new sub-processor here"
    assert sorted(set(REGISTER_NAME_OF.values()) - set(register)) == []


def test_every_vendor_has_a_criticality_a_contract_and_an_exit_plan() -> None:
    exits = {
        short_name(name)
        for row in table_rows(
            section(read("docs/operations/vendor-register.md"), "Exit plans")
        )
        for name in row[0].split(", ")
    }

    for name, row in register_rows().items():
        assert len(row) == 6 and all(row), row
        assert row[2] in CRITICALITY, row
        assert name in exits, f"{name} has no exit plan"


def test_the_offboarding_removes_every_vendor_console() -> None:
    checklist = " ".join(read("docs/operations/offboarding.md").split()).lower()

    assert "24 hours" in checklist
    assert [
        name
        for name in register_rows()
        if name not in WITHOUT_CONSOLE and name.lower() not in checklist
    ] == []


def test_the_vendor_register_was_reviewed_within_a_year() -> None:
    register = read("docs/operations/vendor-register.md")
    match = re.search(r"^Reviewed: ([0-9]{4}-[0-9]{2}-[0-9]{2})\.", register, re.M)

    assert match is not None
    reviewed = date.fromisoformat(match.group(1))
    assert reviewed <= today(), "a review cannot be dated ahead"
    assert today() - reviewed <= LONGEST_GAP


def test_a_tabletop_was_held_or_is_planned_within_a_year() -> None:
    record = section(read("docs/operations/tabletop.md"), "Record")
    rows = [
        (date.fromisoformat(row[0][:10]), PLANNED in row[0])
        for row in table_rows(record)
    ]
    held = [day for day, is_planned in rows if not is_planned]
    planned = [day for day, is_planned in rows if is_planned]

    assert rows, "record the exercise or plan the next one"
    assert all(day <= today() for day in held), "a held exercise lies ahead"
    assert all(today() - day <= OVERDUE_PLAN for day in planned), (
        "a planned exercise has passed: record it, or plan it again"
    )
    assert any(today() - day <= LONGEST_GAP for day in held) or any(
        day - today() <= LONGEST_GAP for day in planned
    )


def test_the_incident_hours_are_italian_time() -> None:
    on_call = read("docs/operations/on-call.md")
    hours = table_rows(section(on_call, "Hours (Europe/Rome)"))

    assert [row[0] for row in hours] == ["SEV1", "SEV2", "SEV3"]
    for document in ("docs/operations/slo.md", "docs/operations/maintenance.md"):
        assert "Europe/Rome" in read(document), document
    for document in DOCUMENTS:
        assert "Tbilisi" not in read(document), document


def test_the_documents_name_only_todays_languages() -> None:
    for document in DOCUMENTS:
        assert FORMER_LANGUAGES.search(read(document)) is None, document


def test_the_product_objectives_page_through_existing_alerts() -> None:
    rows = table_rows(section(read("docs/operations/slo.md"), "Product objectives"))
    alerts = {name for row in rows for name in re.findall(r"`([a-z_]+)`", row[3])}

    assert [row[0].split("**")[1] for row in rows] == list(PRODUCT_OBJECTIVES)
    assert (
        sorted(
            name
            for name in alerts
            if not (REPOSITORY / "ops" / "alerts" / f"{name}.yaml").is_file()
        )
        == []
    )
