"""
The name of a database statement for its span: the operation (select,
insert, update, delete, ...) and the table it works on, read from the
statement's text or from the parts it was composed of. Never its
parameters, which hold customers' data.
"""

import re
from dataclasses import dataclass

from psycopg import sql

UNKNOWN_TABLE: str = "unknown"
TABLE_AFTER_KEYWORD: re.Pattern[str] = re.compile(
    r"\b(?:from|into|update|join|table)\s+((?:\"?[A-Za-z_][\w$]*\"?\.)?\"?[A-Za-z_][\w$]*\"?)",
    re.IGNORECASE,
)
FIRST_WORD: re.Pattern[str] = re.compile(r"[A-Za-z]+")
# Statements that name no table, by their first word.
TABLELESS_OPERATIONS: frozenset[str] = frozenset(
    {"begin", "commit", "rollback", "savepoint", "release", "set", "reset", "listen"}
)


@dataclass(frozen=True)
class StatementLabel:
    """What a span says about one statement: its operation and table."""

    operation: str
    collection: str

    @property
    def span_name(self) -> str:
        if self.operation in TABLELESS_OPERATIONS:
            return self.operation.upper()

        return f"{self.operation.upper()} {self.collection}"


def label_statement(query: object) -> StatementLabel:
    """The label of a statement given as text, bytes or a composed `sql` object."""

    text: str = statement_text(query)
    first: re.Match[str] | None = FIRST_WORD.search(text)
    operation: str = "statement" if first is None else first.group(0).lower()
    if operation == "with":
        # A common table expression: name the statement after its main verb.
        verbs = re.findall(r"\)\s*(select|insert|update|delete)\b", text, re.IGNORECASE)
        operation = verbs[-1].lower() if verbs else "select"

    table: re.Match[str] | None = TABLE_AFTER_KEYWORD.search(text)
    collection: str = (
        UNKNOWN_TABLE
        if table is None
        else table.group(1).replace('"', "").rsplit(".", 1)[-1]
    )
    return StatementLabel(operation=operation, collection=collection)


def statement_text(query: object) -> str:
    """The statement with identifiers in place and no parameters (`%s` stays)."""

    if isinstance(query, str):
        return query

    if isinstance(query, bytes):
        return query.decode("utf-8", errors="replace")

    if isinstance(query, sql.Composable):
        return "".join(composed_parts(query))

    return ""


def composed_parts(query: sql.Composable) -> list[str]:
    """The text of a composed statement without a connection to quote it."""

    if isinstance(query, sql.Composed):
        return [part for item in query for part in composed_parts(item)]

    if isinstance(query, sql.SQL | sql.Identifier):
        return [query.as_string()]

    # Literals and placeholders: their values are never part of a label.
    return ["?"]
