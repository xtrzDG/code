"""
Reading and checking the owner text catalog (`texts/<language>.json`).

The catalog is read once at startup and refused when it is inconsistent: a
file names another language, English is not the reviewed source, a
translation has a key English lacks, names a draft it does not hold, or
uses other `{placeholders}` than English (a dropped `{amount}` would lose
the amount, a new one would fail the rendering). A text missing in a
language is allowed here and falls back to English; the completeness test
(tests/localization/text_catalog) keeps CI from shipping one.
"""

import re
from pathlib import Path

from pydantic import ValidationError

from app.schemas.constants.localization import (
    CABINET_LANGUAGES,
    CabinetLanguage,
    TextReviewStatus,
)
from app.schemas.dto.text_catalog import TextCatalog, TextCatalogFile
from app.schemas.typings.localization.constrained_strings import OwnerTextKey
from app.schemas.typings.localization.strings import LocalizedTextValue

SOURCE_LANGUAGE: CabinetLanguage = CabinetLanguage.ENGLISH
PLACEHOLDER_PATTERN: re.Pattern[str] = re.compile(r"\{([a-z_]+)\}")


class TextCatalogError(ValueError):
    """The catalog files cannot be served (raised at startup)."""


def catalog_file_path(directory: Path, language: CabinetLanguage) -> Path:
    return directory / f"{language.value}.json"


def read_text_catalog(directory: Path) -> TextCatalog:
    """
    Every cabinet language's file of `directory`, checked against English.

    Raises:
        TextCatalogError: a file is missing, malformed or inconsistent.
    """

    files: dict[CabinetLanguage, TextCatalogFile] = {
        language: read_catalog_file(catalog_file_path(directory, language), language)
        for language in CABINET_LANGUAGES
    }
    check_text_catalog(files)
    return TextCatalog(files=files)


def read_catalog_file(path: Path, language: CabinetLanguage) -> TextCatalogFile:
    try:
        catalog_file: TextCatalogFile = TextCatalogFile.model_validate_json(
            path.read_bytes()
        )
    except (OSError, ValidationError) as error:
        raise TextCatalogError(f"{path.name} cannot be read: {error}") from error

    if catalog_file.language is not language:
        raise TextCatalogError(
            f"{path.name} holds the texts of {catalog_file.language.value}."
        )

    return catalog_file


def check_text_catalog(files: dict[CabinetLanguage, TextCatalogFile]) -> None:
    """
    Raises:
        TextCatalogError: the files disagree with the English source.
    """

    source: TextCatalogFile = files[SOURCE_LANGUAGE]
    if source.review_status is not TextReviewStatus.REVIEWED or source.draft_keys:
        raise TextCatalogError("en.json is the source and cannot hold drafts.")

    for language, catalog_file in files.items():
        unknown: list[OwnerTextKey] = [
            key for key in catalog_file.texts if key not in source.texts
        ]
        if unknown:
            raise TextCatalogError(
                f"{language.value}.json has keys en.json lacks: {unknown[:5]}."
            )

        absent_drafts: list[OwnerTextKey] = [
            key for key in catalog_file.draft_keys if key not in catalog_file.texts
        ]
        if absent_drafts:
            raise TextCatalogError(
                f"{language.value}.json names drafts it lacks: {absent_drafts[:5]}."
            )

        for key, value in catalog_file.texts.items():
            if placeholders(value) != placeholders(source.texts[key]):
                raise TextCatalogError(
                    f"{language.value}.json {key} uses other placeholders than English."
                )


def placeholders(text: LocalizedTextValue) -> frozenset[str]:
    """The `{name}` fields of a text template."""

    return frozenset(PLACEHOLDER_PATTERN.findall(str(text)))
