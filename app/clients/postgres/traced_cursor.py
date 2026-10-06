"""
The span wrapper of psycopg: with tracing on, every statement a cursor of
the pool runs is a span named after its operation and table (`SELECT
conversations`), with the database system, the operation and the table as
attributes and the statement's duration as the span's. The parameters and
the statement's text are never recorded.
"""

from collections.abc import Iterable
from string.templatelib import Template
from typing import Any, LiteralString, Self, overload

import psycopg
from psycopg.abc import Params, Query, QueryNoTemplate
from psycopg.rows import TupleRow

from app.schemas.constants.telemetry import SpanKind
from app.utilities.observability.tracing.span_tracer import SpanTracer
from app.utilities.observability.tracing.statement_labels import (
    StatementLabel,
    label_statement,
)

DATABASE_SYSTEM: LiteralString = "postgresql"

type TracedCursorClass = type[psycopg.Cursor[TupleRow]]


def traced_cursor_class(tracer: SpanTracer) -> TracedCursorClass:
    """A cursor class whose statements are spans of `tracer`."""

    class TracedCursor(psycopg.Cursor[TupleRow]):
        @overload
        def execute(
            self,
            query: QueryNoTemplate,
            params: Params | None = None,
            *,
            prepare: bool | None = None,
            binary: bool | None = None,
        ) -> Self: ...

        @overload
        def execute(
            self,
            query: Template,
            *,
            prepare: bool | None = None,
            binary: bool | None = None,
        ) -> Self: ...

        def execute(
            self,
            query: Query,
            params: Params | None = None,
            *,
            prepare: bool | None = None,
            binary: bool | None = None,
        ) -> Self:
            if not tracer.is_recording:
                return self._run(query, params, prepare, binary)

            label: StatementLabel = label_statement(query)
            with tracer.span(label.span_name, SpanKind.CLIENT, span_attributes(label)):
                return self._run(query, params, prepare, binary)

        def _run(
            self,
            query: Query,
            params: Params | None,
            prepare: bool | None,
            binary: bool | None,
        ) -> Self:
            if isinstance(query, Template):
                return super().execute(query, prepare=prepare, binary=binary)

            return super().execute(query, params, prepare=prepare, binary=binary)

        def executemany(
            self,
            query: Query,
            params_seq: Iterable[Params],
            *,
            returning: bool = False,
        ) -> None:
            if not tracer.is_recording:
                super().executemany(query, params_seq, returning=returning)
                return

            label: StatementLabel = label_statement(query)
            with tracer.span(label.span_name, SpanKind.CLIENT, span_attributes(label)):
                super().executemany(query, params_seq, returning=returning)

    return TracedCursor


def span_attributes(label: StatementLabel) -> dict[str, Any]:
    return {
        "db.system": DATABASE_SYSTEM,
        "db.operation.name": label.operation.upper(),
        "db.collection.name": label.collection,
        "sentry.op": "db",
    }
