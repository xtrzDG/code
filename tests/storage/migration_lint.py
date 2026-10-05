"""
A linter for SQL migrations that run while the previous release serves.

It reads the files in version order and remembers which tables earlier
files created; a statement that would block writes to such a table (a
table that may be big and busy by the time the file runs) is a finding:

- a stored generated column (rewrites the table under ACCESS EXCLUSIVE);
- an index built without CONCURRENTLY (blocks writes while it builds);
- UPDATE, DELETE or INSERT ... SELECT over it (one long transaction that
  locks every row it touches; use `workshop backfill-lookup` or a batched
  maintenance command after the deploy);
- a column type change (rewrite), SET NOT NULL (full scan under ACCESS
  EXCLUSIVE) or a constraint added without NOT VALID (full scan).

A file headed `-- workshop:no-transaction` must consist of idempotent
statements, because a failed try runs it again from the top; and only
such a file may build an index CONCURRENTLY. Tables a file creates itself
are new and empty: anything goes for them in that file.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from app.utilities.storage.schema_migration_files import has_no_transaction_header
from app.utilities.storage.sql_statements import (
    code_without_comments,
    split_sql_statements,
)

TABLE: str = r"(?:only\s+)?workshop\.([a-z_][a-z0-9_]*)"
COLLECTION_PATTERN: re.Pattern[str] = re.compile(
    r"workshop\.create_document_collection\(\s*'([a-z_][a-z0-9_]*)'\s*\)"
)
CREATE_TABLE_PATTERN: re.Pattern[str] = re.compile(
    rf"^create\s+(?:unlogged\s+)?table\s+(?:if\s+not\s+exists\s+)?{TABLE}"
)
ALTER_TABLE_PATTERN: re.Pattern[str] = re.compile(
    rf"^alter\s+table\s+(?:if\s+exists\s+)?{TABLE}"
)
CREATE_INDEX_PATTERN: re.Pattern[str] = re.compile(
    r"^create\s+(?:unique\s+)?index\s+(concurrently\s+)?(if\s+not\s+exists\s+)?"
    rf"[a-z_0-9\"]*\s*on\s+{TABLE}"
)
DATA_CHANGE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(rf"^update\s+{TABLE}"),
    re.compile(rf"^delete\s+from\s+{TABLE}"),
    re.compile(rf"^insert\s+into\s+workshop\.[a-z_0-9]+.*\bselect\b.*\bfrom\s+{TABLE}"),
)
REWRITES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"generated\s+always\s+as\s*\(.*\)\s*stored"),
        "a stored generated column",
    ),
    (
        re.compile(r"alter\s+column\s+\S+\s+(?:set\s+data\s+)?type\b"),
        "a column type change",
    ),
    (re.compile(r"alter\s+column\s+\S+\s+set\s+not\s+null"), "SET NOT NULL"),
    (
        re.compile(
            r"add\s+(?:constraint\s+\S+\s+)?(?:check|foreign\s+key)\b(?!.*not\s+valid)"
        ),
        "a constraint without NOT VALID",
    ),
)
IDEMPOTENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^create\s+(?:unique\s+)?index\s+concurrently\s+if\s+not\s+exists\s"),
    re.compile(r"^drop\s+index\s+concurrently\s+if\s+exists\s"),
    re.compile(r"^create\s+or\s+replace\s+(?:function|procedure|view|trigger)\s"),
    re.compile(r"^create\s+(?:table|schema)\s+if\s+not\s+exists\s"),
    re.compile(
        r"^alter\s+table\s+(?:if\s+exists\s+)?\S+\s+add\s+column\s+if\s+not\s+exists\s"
    ),
    re.compile(r"^comment\s+on\s"),
    re.compile(
        r"^select\s+workshop\.(?:add_lookup_column|create_document_collection)\("
    ),
)
TRANSACTION_CONTROL: re.Pattern[str] = re.compile(
    r"^(?:begin|commit|rollback|start\s+transaction)\b"
)
DOLLAR_QUOTED: re.Pattern[str] = re.compile(r"\$([a-z_]*)\$.*?\$\1\$", re.DOTALL)


@dataclass(frozen=True)
class Finding:
    migration: str
    statement: str
    problem: str

    def describe(self) -> str:
        return f"{self.migration}: {self.problem} in `{self.statement[:120]}`"


def normalized_statements(sql_text: str) -> list[str]:
    """Statements in lower case with single spaces, comments and bodies out."""

    statements: list[str] = []
    for statement in split_sql_statements(sql_text):
        code: str = code_without_comments(str(statement)).lower()
        code = DOLLAR_QUOTED.sub("$$", code)
        statements.append(" ".join(code.split()))

    return [statement for statement in statements if statement]


def created_tables(statement: str) -> set[str]:
    tables: set[str] = set(COLLECTION_PATTERN.findall(statement))
    created: re.Match[str] | None = CREATE_TABLE_PATTERN.match(statement)
    if created is not None:
        tables.add(created.group(1))

    return tables


def lint_file(name: str, sql_text: str, existing: set[str]) -> list[Finding]:
    """The findings of one file, given the tables earlier files created."""

    is_transactional: bool = not has_no_transaction_header(sql_text)
    new_tables: set[str] = set()
    findings: list[Finding] = []
    for statement in normalized_statements(sql_text):
        new_tables |= created_tables(statement)
        old_tables: set[str] = existing - new_tables
        findings.extend(
            Finding(name, statement, problem)
            for problem in statement_problems(statement, old_tables, is_transactional)
        )

    return findings


def statement_problems(
    statement: str, old_tables: set[str], is_transactional: bool
) -> list[str]:
    problems: list[str] = []
    if TRANSACTION_CONTROL.match(statement):
        problems.append("transaction control (the runner owns transactions)")

    if not is_transactional and not any(
        p.match(statement) for p in IDEMPOTENT_PATTERNS
    ):
        problems.append("a statement a new try could not run again (not idempotent)")

    index: re.Match[str] | None = CREATE_INDEX_PATTERN.match(statement)
    if index is not None:
        is_concurrent: bool = index.group(1) is not None
        if is_concurrent and is_transactional:
            problems.append("CREATE INDEX CONCURRENTLY outside a no-transaction file")
        if not is_concurrent and index.group(3) in old_tables:
            problems.append(f"an index on {index.group(3)} built without CONCURRENTLY")

    altered: re.Match[str] | None = ALTER_TABLE_PATTERN.match(statement)
    if altered is not None and altered.group(1) in old_tables:
        problems.extend(
            f"{label} on {altered.group(1)}"
            for pattern, label in REWRITES
            if pattern.search(statement)
        )

    for pattern in DATA_CHANGE_PATTERNS:
        changed: re.Match[str] | None = pattern.match(statement)
        if changed is not None and changed.group(1) in old_tables:
            problems.append(
                f"an unbatched data change over {changed.group(1)} "
                "(backfill after the deploy: workshop backfill-lookup)"
            )

    return problems


def lint_directory(directory: Path, exempt: frozenset[str]) -> list[Finding]:
    """Findings of every file not in `exempt`, in version order."""

    existing: set[str] = set()
    findings: list[Finding] = []
    for path in sorted(directory.glob("*.sql")):
        sql_text: str = path.read_text(encoding="utf-8")
        if path.stem not in exempt:
            findings.extend(lint_file(path.stem, sql_text, existing))
        for statement in normalized_statements(sql_text):
            existing |= created_tables(statement)

    return findings
