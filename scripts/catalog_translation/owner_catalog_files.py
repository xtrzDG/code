"""
The owner text catalog files as the translation script edits them: read
with the same checks the service runs at startup (a language without a
file yet starts empty), written back in the order of the English source so
a diff shows only what changed.
"""

import json
from pathlib import Path

from app.registries.localization.text_catalog_registry import TextCatalogRegistry
from app.schemas.constants.localization import (
    CABINET_LANGUAGES,
    CabinetLanguage,
    TextReviewStatus,
)
from app.schemas.dto.text_catalog import TextCatalog, TextCatalogFile
from app.schemas.typings.localization.constrained_strings import OwnerTextKey
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.utilities.localization.text_catalog_files import (
    SOURCE_LANGUAGE,
    catalog_file_path,
    check_text_catalog,
    read_catalog_file,
)


def load_catalog(directory: Path) -> TextCatalog:
    """
    Every cabinet language's file, checked against English; a language
    with no file yet (a new cabinet language) starts as an empty draft.

    Raises:
        TextCatalogError: a file is malformed or disagrees with English.
    """

    files: dict[CabinetLanguage, TextCatalogFile] = {}
    for language in CABINET_LANGUAGES:
        path: Path = catalog_file_path(directory, language)
        files[language] = (
            read_catalog_file(path, language)
            if path.exists() or language is SOURCE_LANGUAGE
            else TextCatalogFile(
                language=language,
                review_status=TextReviewStatus.NEEDS_REVIEW,
                texts={},
            )
        )
    check_text_catalog(files)
    return TextCatalog(files=files)


def with_drafts(
    catalog: TextCatalog,
    language: CabinetLanguage,
    drafts: dict[OwnerTextKey, LocalizedTextValue],
) -> TextCatalogFile:
    """
    The language's file with new drafted texts. A reviewed file names them
    in `draft_keys`; a file of drafts is NEEDS_REVIEW as a whole already.
    """

    current: TextCatalogFile = catalog.files[language]
    texts: dict[OwnerTextKey, LocalizedTextValue] = current.texts | drafts
    draft_keys: set[OwnerTextKey] = set(current.draft_keys)
    if current.review_status is TextReviewStatus.REVIEWED:
        draft_keys |= set(drafts)

    return in_source_order(
        catalog,
        current.model_copy(update={"texts": texts, "draft_keys": list(draft_keys)}),
    )


def as_reviewed(
    catalog: TextCatalog,
    language: CabinetLanguage,
    keys: list[OwnerTextKey] | None,
) -> TextCatalogFile:
    """
    The language's file after a native speaker checked some drafted texts
    (`keys`) or the whole file (None: every text, the file turns reviewed).
    """

    current: TextCatalogFile = catalog.files[language]
    if keys is None:
        return current.model_copy(
            update={"review_status": TextReviewStatus.REVIEWED, "draft_keys": []}
        )

    return current.model_copy(
        update={"draft_keys": [key for key in current.draft_keys if key not in keys]}
    )


def in_source_order(
    catalog: TextCatalog, catalog_file: TextCatalogFile
) -> TextCatalogFile:
    order: list[OwnerTextKey] = TextCatalogRegistry(catalog).list_keys()
    return catalog_file.model_copy(
        update={
            "texts": {
                key: catalog_file.texts[key]
                for key in order
                if key in catalog_file.texts
            },
            "draft_keys": [key for key in order if key in catalog_file.draft_keys],
        }
    )


def write_catalog_file(directory: Path, catalog_file: TextCatalogFile) -> Path:
    """The file as the repository keeps it: two-space JSON, letters unescaped."""

    path: Path = catalog_file_path(directory, catalog_file.language)
    path.write_text(
        json.dumps(catalog_file.model_dump(mode="json"), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return path


def catalog_report(catalog: TextCatalog) -> list[str]:
    """One line per language: missing texts and texts that wait for review."""

    registry = TextCatalogRegistry(catalog)
    keys: list[OwnerTextKey] = registry.list_keys()
    lines: list[str] = []
    for language in CABINET_LANGUAGES:
        missing: int = len(registry.list_missing_keys(language))
        drafts: int = sum(
            1
            for key in keys
            if registry.review_status(key, language) is TextReviewStatus.NEEDS_REVIEW
        )
        lines.append(
            f"{language.value}: {len(keys) - missing}/{len(keys)} texts, "
            f"{missing} missing, {drafts} waiting for review"
        )

    return lines
