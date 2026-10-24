"""Splitting a no-transaction migration file into its statements."""

from app.utilities.storage.schema_migration_files import has_no_transaction_header
from app.utilities.storage.sql_statements import (
    code_without_comments,
    split_sql_statements,
)


def test_statements_split_on_semicolons_outside_literals_and_comments() -> None:
    sql_text = (
        "-- workshop:no-transaction\n"
        "-- a comment; with a semicolon\n"
        "create index concurrently if not exists a_idx on workshop.a (x);\n"
        "/* block; /* nested; */ still comment; */\n"
        "select 'it''s; fine', E'back\\'slash;', \"odd;name\";\n"
        "create or replace function workshop.f() returns trigger\n"
        "language plpgsql as $body$ begin perform 1; return new; end; $body$;\n"
        "select $$plain; body$$, a$b, $1\n"
    )

    statements = [str(statement) for statement in split_sql_statements(sql_text)]

    assert statements == [
        "-- workshop:no-transaction\n-- a comment; with a semicolon\n"
        "create index concurrently if not exists a_idx on workshop.a (x)",
        "/* block; /* nested; */ still comment; */\n"
        "select 'it''s; fine', E'back\\'slash;', \"odd;name\"",
        "create or replace function workshop.f() returns trigger\n"
        "language plpgsql as $body$ begin perform 1; return new; end; $body$",
        "select $$plain; body$$, a$b, $1",
    ]


def test_comment_only_and_empty_parts_are_dropped() -> None:
    assert split_sql_statements("-- only a comment\n;;  \n/* x */;") == []
    assert split_sql_statements("") == []


def test_unterminated_literals_end_with_the_text() -> None:
    assert [str(s) for s in split_sql_statements("select 'open; string")] == [
        "select 'open; string"
    ]
    assert [str(s) for s in split_sql_statements("select $q$ open; body")] == [
        "select $q$ open; body"
    ]
    assert split_sql_statements("/* never closed; ") == []


def test_code_without_comments_keeps_literals() -> None:
    assert code_without_comments("select '--x' -- note\n, 1 /* y */") == (
        "select '--x'  , 1  "
    )


def test_the_no_transaction_header_is_read_before_the_first_statement() -> None:
    assert has_no_transaction_header("-- 1122_x\n--\n-- workshop:no-transaction\n")
    assert has_no_transaction_header("\r\n-- workshop:no-transaction\r\nselect 1;")
    assert not has_no_transaction_header("select 1;\n-- workshop:no-transaction\n")
    assert not has_no_transaction_header("-- workshop:no-transactions\nselect 1;")
    assert not has_no_transaction_header("-- only comments\n")
