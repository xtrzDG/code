"""
Owner-facing texts exist in every cabinet language and come from the owner
text catalog (`app/registries/localization/texts/<language>.json`).

The cabinet shows Georgian, Russian, English, Hebrew and German
(CABINET_LANGUAGES); a plan, a niche question, a staff alert, a forwarding
step or a billing notice in English inside a Hebrew cabinet is the defect
this policy prevents. English stays the only fallback, for a language
added to the cabinet before its catalog file. Issued invoices and receipts
are the exception the other way round: they are kept as printed, so they
carry reviewed languages only and a language of drafts reads English.

Owner texts are not written as literals in code: the modules that hold
them (owner_text_sources.OWNER_TEXT_MODULES and the niche templates) read
the catalog, so a translator edits one file per language.
"""

import ast
from pathlib import Path

from app.schemas.constants.localization import CABINET_LANGUAGES, TextReviewStatus
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.owner_texts import OWNER_TEXT_CATALOG
from tests.architecture_policy.owner_text_sources import (
    CUSTOMER_TEXT_NAMES,
    ISSUED_DOCUMENT_MODULES,
    OWNER_TEXT_MODULES,
    cabinet_language_texts,
    issued_document_texts,
)

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
NICHE_TEMPLATE_DIRECTORY: Path = PROJECT_ROOT / "app" / "registries" / "niches"
# Text builders that take literal values per language.
LITERAL_TEXT_BUILDERS: frozenset[str] = frozenset(
    {"build_localized_text", "localized", "LocalizedText"}
)
# Niche modules that are not owner texts: English for the model, or the
# starter answers customers read in the business's languages.
NICHE_MODULES_WITHOUT_OWNER_TEXTS: dict[str, str] = {
    "examples": "example exchanges are English text for the model",
    "starters": "starter answers are drafts of what customers read",
}


def missing_languages(text: LocalizedText) -> list[str]:
    tags: set[LanguageTag] = set(text.values)
    return [
        language.value
        for language in CABINET_LANGUAGES
        if LanguageTag(language.value) not in tags
    ]


def test_every_owner_facing_text_covers_the_cabinet_languages() -> None:
    texts: list[LocalizedText] = cabinet_language_texts()
    gaps: list[str] = [
        f"{text.values[LanguageTag('en')][:60]!r}: {missing_languages(text)}"
        for text in texts
        if missing_languages(text)
    ]

    assert len(texts) > 500
    assert gaps == [], "Owner texts without every cabinet language:\n" + "\n".join(gaps)


def test_issued_documents_carry_reviewed_languages_only() -> None:
    reviewed: set[LanguageTag] = {
        LanguageTag(language.value)
        for language, catalog_file in OWNER_TEXT_CATALOG.files.items()
        if catalog_file.review_status is TextReviewStatus.REVIEWED
    }
    texts: list[LocalizedText] = issued_document_texts()

    assert len(texts) > 40
    for text in texts:
        assert LanguageTag("en") in text.values
        assert set(text.values) <= reviewed, text.values[LanguageTag("en")]
    assert {language for text in texts for language in text.values} == reviewed


def literal_text_lines(path: Path) -> list[int]:
    """Lines where a text builder gets a string literal for a language."""

    tree: ast.Module = ast.parse(path.read_text(encoding="utf-8"))
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id not in LITERAL_TEXT_BUILDERS:
            continue
        values: list[ast.expr] = [keyword.value for keyword in node.keywords]
        values.extend(
            item
            for keyword in node.keywords
            if isinstance(keyword.value, ast.Dict)
            for item in keyword.value.values
            if item is not None
        )
        if any(is_string_literal(value) for value in values):
            lines.append(node.lineno)

    return lines


def is_string_literal(value: ast.expr) -> bool:
    """A string, or a string wrapped in a primitive: LocalizedTextValue("…")."""

    if isinstance(value, ast.Call) and len(value.args) == 1:
        value = value.args[0]
    return isinstance(value, ast.Constant) and isinstance(value.value, str)


def owner_text_paths() -> list[Path]:
    paths: list[Path] = [
        PROJECT_ROOT / (module.replace(".", "/") + ".py")
        for module in (*OWNER_TEXT_MODULES, *ISSUED_DOCUMENT_MODULES)
    ]
    paths.extend(
        path
        for path in sorted(NICHE_TEMPLATE_DIRECTORY.rglob("*.py"))
        if path.parent.name not in NICHE_MODULES_WITHOUT_OWNER_TEXTS
    )
    return paths


def test_owner_texts_are_read_from_the_catalog_not_written_in_code() -> None:
    customer_lines: set[tuple[str, str]] = {
        tuple(name.rsplit(".", 1)) for name in CUSTOMER_TEXT_NAMES
    }
    found: list[str] = []
    for path in owner_text_paths():
        module: str = path.relative_to(PROJECT_ROOT).with_suffix("").as_posix()
        source: str = path.read_text(encoding="utf-8")
        for line in literal_text_lines(path):
            statement: str = source.splitlines()[line - 1].split(":")[0].strip()
            if (module.replace("/", "."), statement) in customer_lines:
                continue
            found.append(f"{module}.py:{line}")

    assert found == [], (
        "Owner texts written as literals; add them to "
        "app/registries/localization/texts/<language>.json and read them with "
        "owner_text():\n" + "\n".join(found)
    )


def test_a_literal_text_is_found(tmp_path: Path) -> None:
    path = tmp_path / "texts.py"
    path.write_text(
        'TITLE = localized(en="New booking", ru="Новая бронь")\n'
        'NAME = LocalizedText(values={EN: LocalizedTextValue("Chat")})\n'
        'READ = owner_text("plans.chat.name")\n'
        'JOINED = LocalizedText(values={EN: LocalizedTextValue(f"{a} {b}")})\n',
        encoding="utf-8",
    )

    assert literal_text_lines(path) == [1, 2]
