"""
The card number scan of exports (scripts/card_number_scan.py, PAY-01): a
dump's column, a log line or a text with a Luhn-valid card number is
reported by file and line without its digits; ids, phone numbers, masked
cards and other numbers are not; a file that cannot be read proves nothing.
"""

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts.card_number_scan import EXIT_CLEAN, EXIT_FOUND, EXIT_UNREADABLE, main

CLEAN_LINES: tuple[str, ...] = (
    "msg_01\t[card number] cvv [security code]\t2026-11-03 12:00:00+00",
    "bkg_4242424242424242\t42424242-4242-4242-4242-424242424242",
    '{"message": "call +39 347 123 4567", "amount_minor": 150000}',
    "Order 4242424242424241: the Luhn check fails.",
)


def run(*arguments: str) -> tuple[int, str, str]:
    output, errors = io.StringIO(), io.StringIO()
    with redirect_stdout(output), redirect_stderr(errors):
        code = main(list(arguments))
    return code, output.getvalue(), errors.getvalue()


def test_a_card_in_a_column_or_a_log_line_is_reported_without_its_digits(
    tmp_path: Path,
) -> None:
    export = tmp_path / "dump.sql"
    export.write_text(
        "\n".join(
            [
                *CLEAN_LINES,
                "msg_02\tmy card is 4242 4242 4242 4242\t2026-11-03",
                '{"message": "paid with 5555555555554444"}',
            ]
        ),
        encoding="utf-8",
    )

    code, output, _ = run(str(export))

    assert code == EXIT_FOUND
    assert f"{export}:5: 1 card number(s)" in output
    assert f"{export}:6: 1 card number(s)" in output
    assert "4242" not in output and "5555" not in output
    assert "2 line(s) with a card number in 1 file(s)." in output


def test_exports_without_a_card_pass(tmp_path: Path) -> None:
    export = tmp_path / "logs.jsonl"
    export.write_text("\n".join(CLEAN_LINES), encoding="utf-8")

    code, output, _ = run(str(export))

    assert code == EXIT_CLEAN
    assert output == "0 line(s) with a card number in 1 file(s).\n"


def test_a_file_that_cannot_be_read_proves_nothing(tmp_path: Path) -> None:
    code, _, errors = run(str(tmp_path / "missing.sql"))

    assert code == EXIT_UNREADABLE
    assert "missing.sql: cannot be read" in errors
