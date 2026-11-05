"""
The payments document (docs/security/payments.md) stays true: the code it
cites exists, every place it says masks card numbers does call the
masking, the evals it names are played, and the responsibility matrix
gives each duty to someone.
"""

import re
from pathlib import Path

from tests.legal.governance_documents import (
    REPOSITORY,
    missing_paths,
    read,
    section,
    table_rows,
)

PAYMENTS: str = "docs/security/payments.md"
MASKING_MODULE: str = "app.utilities.privacy.sensitive_numbers"
FILE_IN_BACKTICKS: re.Pattern[str] = re.compile(r"`((?:[\w.-]+/)*[\w.-]+\.py)`")
EVAL_ID: re.Pattern[str] = re.compile(r"`(carddata__\w+)`")


def code_file(name: str) -> Path:
    """The file a cell names: a path, or a module name found under app/."""

    path: Path = REPOSITORY / name
    if path.exists():
        return path

    found: list[Path] = sorted((REPOSITORY / "app").rglob(name))
    assert len(found) == 1, f"{name!r} names {len(found)} files"
    return found[0]


def test_every_path_in_the_payments_document_exists() -> None:
    assert missing_paths(read(PAYMENTS)) == []


def test_every_place_said_to_mask_card_numbers_calls_the_masking() -> None:
    rows = table_rows(
        section(read(PAYMENTS), "Card numbers customers type or say anyway")
    )

    files: list[str] = [
        name for _, cell in rows for name in FILE_IN_BACKTICKS.findall(cell)
    ]

    assert len(files) >= 9
    for name in files:
        source: str = code_file(name).read_text(encoding="utf-8")
        assert MASKING_MODULE in source, f"{name} does not mask card numbers"


def test_the_card_evals_it_names_are_played() -> None:
    dataset: str = read("evals/datasets/restaurant.yaml")
    named: list[str] = EVAL_ID.findall(read(PAYMENTS))

    assert named == ["carddata__it", "carddata__en"]
    for scenario in named:
        assert f"- id: {scenario}\n" in dataset


def test_each_duty_of_the_matrix_says_what_the_platform_does() -> None:
    rows = table_rows(section(read(PAYMENTS), "Responsibility matrix for businesses"))

    assert len(rows) >= 8
    for duty, business, platform, _provider in rows:
        assert duty and business and platform, duty


def test_the_document_is_listed_with_its_test() -> None:
    index: str = read("docs/security/README.md")

    assert "`docs/security/payments.md`" in index
    assert "`tests/legal/test_payments_document.py`" in index
