"""
The owner text catalog of this process and its lookups.

The catalog (`app/registries/localization/texts/<language>.json`) is read
and checked when this module is first imported, so a broken file stops the
API and the worker at startup, never at the first message. Catalog texts
are built into module constants and registries at import, so an unknown key
fails at startup too.

Values come in a fixed order (English, Russian, Georgian, then the newer
cabinet languages) so a LocalizedText reads the same in every process.
"""

from pathlib import Path

from app.schemas.constants.localization import CabinetLanguage
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.text_catalog import TextCatalog, TextCatalogFile
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    OwnerTextKey,
)
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.utilities.knowledge.localized_texts import RULE_LINE_SEPARATOR
from app.utilities.localization.text_catalog_files import (
    SOURCE_LANGUAGE,
    TextCatalogError,
    read_text_catalog,
)

OWNER_TEXTS_DIRECTORY: Path = (
    Path(__file__).resolve().parents[2] / "registries" / "localization" / "texts"
)
VALUE_ORDER: tuple[CabinetLanguage, ...] = (
    CabinetLanguage.ENGLISH,
    CabinetLanguage.RUSSIAN,
    CabinetLanguage.GEORGIAN,
    CabinetLanguage.HEBREW,
    CabinetLanguage.GERMAN,
)

OWNER_TEXT_CATALOG: TextCatalog = read_text_catalog(OWNER_TEXTS_DIRECTORY)


def owner_text(key: str, catalog: TextCatalog = OWNER_TEXT_CATALOG) -> LocalizedText:
    """
    The catalog text of a key (a source literal such as "plans.chat.name")
    in every language that has it.

    Raises:
        TextCatalogError: en.json has no such key.
    """

    text_key: OwnerTextKey = require_key(OwnerTextKey(key), catalog)
    return LocalizedText(
        values={
            LanguageTag(language.value): catalog.files[language].texts[text_key]
            for language in VALUE_ORDER
            if text_key in catalog.files[language].texts
        }
    )


def has_owner_text(key: str, catalog: TextCatalog = OWNER_TEXT_CATALOG) -> bool:
    return OwnerTextKey(key) in catalog.files[SOURCE_LANGUAGE].texts


def owner_rule_lines(
    prefix: str,
    catalog: TextCatalog = OWNER_TEXT_CATALOG,
) -> LocalizedText:
    """
    The numbered texts `<prefix>.1`, `<prefix>.2`, ... as one rule per line.

    A language shows the list only when it has every line, so a list never
    mixes languages; otherwise the language reads the English list.

    Raises:
        TextCatalogError: en.json has no `<prefix>.1`.
    """

    keys: list[OwnerTextKey] = numbered_keys(prefix, catalog)
    if keys == []:
        raise TextCatalogError(f"en.json has no numbered texts under {prefix}.")

    values: dict[LanguageTag, LocalizedTextValue] = {}
    for language in VALUE_ORDER:
        texts: dict[OwnerTextKey, LocalizedTextValue] = catalog.files[language].texts
        if all(key in texts for key in keys):
            values[LanguageTag(language.value)] = LocalizedTextValue(
                RULE_LINE_SEPARATOR.join(str(texts[key]) for key in keys)
            )

    return LocalizedText(values=values)


def owner_text_list(
    prefix: str,
    catalog: TextCatalog = OWNER_TEXT_CATALOG,
) -> tuple[LocalizedText, ...]:
    """
    The numbered texts `<prefix>.1`, `<prefix>.2`, ... each on its own (the
    steps of a guide).

    Raises:
        TextCatalogError: en.json has no `<prefix>.1`.
    """

    keys: list[OwnerTextKey] = numbered_keys(prefix, catalog)
    if keys == []:
        raise TextCatalogError(f"en.json has no numbered texts under {prefix}.")

    return tuple(owner_text(str(key), catalog) for key in keys)


def filled_owner_text(
    key: str,
    catalog: TextCatalog = OWNER_TEXT_CATALOG,
    **values: str,
) -> LocalizedText:
    """
    A catalog text with some of its placeholders filled now in every
    language (a carrier's name); the others stay for the later rendering.
    """

    text: LocalizedText = owner_text(key, catalog)
    filled: dict[LanguageTag, LocalizedTextValue] = {}
    for language, template in text.values.items():
        value: str = str(template)
        for name, replacement in values.items():
            value = value.replace("{" + name + "}", replacement)
        filled[language] = LocalizedTextValue(value)

    return LocalizedText(values=filled)


def numbered_keys(prefix: str, catalog: TextCatalog) -> list[OwnerTextKey]:
    source: TextCatalogFile = catalog.files[SOURCE_LANGUAGE]
    keys: list[OwnerTextKey] = []
    while (key := OwnerTextKey(f"{prefix}.{len(keys) + 1}")) in source.texts:
        keys.append(key)

    return keys


def require_key(key: OwnerTextKey, catalog: TextCatalog) -> OwnerTextKey:
    if key not in catalog.files[SOURCE_LANGUAGE].texts:
        raise TextCatalogError(f"en.json has no text {key}.")

    return key
