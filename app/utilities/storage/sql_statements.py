"""
SQL statements of a migration file, one at a time (pure functions).

A `-- workshop:no-transaction` file runs its statements one by one: Postgres
runs several statements sent together as one implicit transaction, where
`CREATE INDEX CONCURRENTLY` is refused. The split follows the lexical rules
of Postgres closely enough for migration files: semicolons inside comments
(`--`, nested `/* */`), string constants (`'...'` with `''`, `E'...'` with
backslash escapes), quoted identifiers and dollar-quoted bodies (`$$`,
`$fn$`) do not end a statement.
"""

import re

from app.schemas.typings.storage.strings import SchemaMigrationStatement

DOLLAR_TAG_PATTERN: re.Pattern[str] = re.compile(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$")
IDENTIFIER_CHARACTERS: frozenset[str] = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$"
)


def split_sql_statements(sql_text: str) -> list[SchemaMigrationStatement]:
    """
    The statements of `sql_text` in order, without their semicolons and
    surrounding blanks; parts holding only comments and blanks are dropped.
    """

    statements: list[SchemaMigrationStatement] = []
    start: int = 0
    has_code: bool = False
    index: int = 0
    while index < len(sql_text):
        skipped_to: int | None = skip_comment(sql_text, index)
        if skipped_to is not None:
            index = skipped_to
            continue

        character: str = sql_text[index]
        if character == ";":
            if has_code:
                statements.append(
                    SchemaMigrationStatement(sql_text[start:index].strip())
                )
            start, has_code, index = index + 1, False, index + 1
            continue

        if not character.isspace():
            has_code = True

        index = skip_literal(sql_text, index)

    if has_code:
        statements.append(SchemaMigrationStatement(sql_text[start:].strip()))

    return statements


def code_without_comments(sql_text: str) -> str:
    """The text with every comment replaced by a space (literals kept)."""

    parts: list[str] = []
    index: int = 0
    while index < len(sql_text):
        skipped_to: int | None = skip_comment(sql_text, index)
        if skipped_to is not None:
            parts.append(" ")
            index = skipped_to
            continue

        next_index: int = skip_literal(sql_text, index)
        parts.append(sql_text[index:next_index])
        index = next_index

    return "".join(parts)


def skip_comment(sql_text: str, index: int) -> int | None:
    """Where a comment starting at `index` ends, or None if none starts there."""

    if sql_text.startswith("--", index):
        line_end: int = sql_text.find("\n", index)
        return len(sql_text) if line_end == -1 else line_end + 1

    if not sql_text.startswith("/*", index):
        return None

    depth: int = 0
    position: int = index
    while position < len(sql_text):
        if sql_text.startswith("/*", position):
            depth += 1
            position += 2
        elif sql_text.startswith("*/", position):
            depth -= 1
            position += 2
            if depth == 0:
                return position
        else:
            position += 1

    return len(sql_text)


def skip_literal(sql_text: str, index: int) -> int:
    """
    Where the token starting at `index` ends: past a whole string constant,
    quoted identifier or dollar-quoted body, else past one character.
    """

    character: str = sql_text[index]
    if character == "'":
        return skip_quoted(sql_text, index, "'", is_escape_string(sql_text, index))

    if character == '"':
        return skip_quoted(sql_text, index, '"', has_backslash_escapes=False)

    if character == "$" and not follows_identifier(sql_text, index):
        tag: re.Match[str] | None = DOLLAR_TAG_PATTERN.match(sql_text, index)
        if tag is not None:
            body_end: int = sql_text.find(tag.group(0), tag.end())
            return len(sql_text) if body_end == -1 else body_end + len(tag.group(0))

    return index + 1


def skip_quoted(
    sql_text: str,
    index: int,
    quote: str,
    has_backslash_escapes: bool,
) -> int:
    position: int = index + 1
    while position < len(sql_text):
        character: str = sql_text[position]
        if (
            has_backslash_escapes
            and character == "\\"
            or character == quote
            and sql_text.startswith(quote * 2, position)
        ):
            position += 2
        elif character == quote:
            return position + 1
        else:
            position += 1

    return len(sql_text)


def is_escape_string(sql_text: str, quote_index: int) -> bool:
    """`E'...'`: the quote follows a lone E (not the end of a longer word)."""

    return (
        quote_index >= 1
        and sql_text[quote_index - 1] in "eE"
        and not follows_identifier(sql_text, quote_index - 1)
    )


def follows_identifier(sql_text: str, index: int) -> bool:
    return index >= 1 and sql_text[index - 1] in IDENTIFIER_CHARACTERS
