"""
The log inventory (docs/security/log-inventory.md, LOG-03) names every
named logger, security event, log context field and audit entry field the
code has: a new one fails here until it is listed.
"""

import ast
import re
from pathlib import Path

from app.operators.business_scoped_pipeline_operator import JOB_TENANT_MISMATCH
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.observability import LogContext
from app.utilities.observability import security_events

ROOT: Path = Path(__file__).resolve().parents[2]
INVENTORY: Path = ROOT / "docs" / "security" / "log-inventory.md"
SECURITY_INDEX: Path = ROOT / "docs" / "security" / "README.md"
NAMED_LOGGER: re.Pattern[str] = re.compile(r"""getLogger\(\s*["'](app\.[a-z_.]+)["']""")
EVENT_NAME: re.Pattern[str] = re.compile(r"^[a-z]+(?:_[a-z]+)+$")
# Bookkeeping fields every stored document has.
DOCUMENT_BOOKKEEPING: frozenset[str] = frozenset({"schema_version", "updated_at"})


def inventory_text() -> str:
    return INVENTORY.read_text(encoding="utf-8")


def named_loggers() -> set[str]:
    return {
        name
        for path in (ROOT / "app").rglob("*.py")
        for name in NAMED_LOGGER.findall(path.read_text(encoding="utf-8"))
    }


def security_event_names() -> set[str]:
    """The string constants of security_events.py that name an event."""

    source = Path(str(security_events.__file__)).read_text(encoding="utf-8")
    names: set[str] = set()
    for node in ast.parse(source).body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
            and EVENT_NAME.fullmatch(node.value.value)
        ):
            names.add(node.value.value)
    return names | {JOB_TENANT_MISMATCH}


def test_every_named_logger_is_listed() -> None:
    loggers = named_loggers()

    assert {"app.security", "app.payments", "app.widget"} <= loggers
    assert {name for name in loggers if f"`{name}`" not in inventory_text()} == set()


def test_every_security_event_is_listed() -> None:
    events = security_event_names()

    assert len(events) >= 7
    assert {name for name in events if f"`{name}`" not in inventory_text()} == set()


def test_every_log_context_field_is_listed() -> None:
    fields = set(LogContext.model_fields)

    assert {name for name in fields if f"`{name}`" not in inventory_text()} == set()


def test_every_audit_entry_field_is_listed() -> None:
    fields = set(AuditLogEntryDocument.model_fields) - DOCUMENT_BOOKKEEPING

    assert {"user_agent", "request_id", "outcome"} <= fields
    assert {name for name in fields if f"`{name}`" not in inventory_text()} == set()


def test_the_security_index_links_the_inventory() -> None:
    assert "`docs/security/log-inventory.md`" in SECURITY_INDEX.read_text(
        encoding="utf-8"
    )
