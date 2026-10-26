"""
The checks of an admin's wording before it is stored: the field exists in
the code template, the language is one of the cabinet's, the text fits the
field and keeps the `{placeholders}` of the code's text. Each text is one
line without HTML already (`NicheOverrideText`).
"""

import re
from collections.abc import Sequence

from app.schemas.constants.localization import CABINET_LANGUAGES
from app.schemas.domain.niche_texts import NicheTextEntry
from app.schemas.dto.niche_texts.niche_text_commands import NicheTextInput
from app.schemas.dto.niche_texts.niche_text_fields import (
    NicheTextCatalog,
    NicheTextField,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.niches.constrained_strings import (
    NicheOverrideText,
    NicheTextFieldKey,
)
from app.utilities.knowledge.localized_texts import FALLBACK_LANGUAGE_TAG

PLACEHOLDER_PATTERN: re.Pattern[str] = re.compile(r"\{([a-z_]+)\}")
EDITABLE_LANGUAGES: tuple[LanguageTag, ...] = tuple(
    LanguageTag(language.value) for language in CABINET_LANGUAGES
)


def check_language(language: LanguageTag) -> LanguageTag:
    """
    Raises:
        ValidationFailedError: not a language the cabinet is translated into.
    """

    if language not in EDITABLE_LANGUAGES:
        names: str = ", ".join(str(tag) for tag in EDITABLE_LANGUAGES)
        raise ValidationFailedError(
            f"Niche texts are edited in the cabinet's languages ({names})."
        )

    return language


def check_draft_texts(
    catalog: NicheTextCatalog,
    language: LanguageTag,
    texts: Sequence[NicheTextInput],
) -> list[NicheTextEntry]:
    """
    The draft's entries of one language; a text equal to the code's own
    wording overrides nothing and is left out.

    Raises:
        ValidationFailedError: an unknown or repeated field, a language the
            cabinet does not speak, a text too long for its field or one
            that drops or adds a placeholder.
    """

    check_language(language)
    fields: dict[NicheTextFieldKey, NicheTextField] = {
        field.field_key: field for field in catalog.fields
    }
    entries: list[NicheTextEntry] = []
    seen: set[NicheTextFieldKey] = set()
    for item in texts:
        field: NicheTextField | None = fields.get(item.field_key)
        if field is None:
            raise ValidationFailedError(
                f"The {catalog.niche_key} template has no text {item.field_key}."
            )
        if item.field_key in seen:
            raise ValidationFailedError(f"{item.field_key} is given twice.")

        seen.add(item.field_key)
        problem: str | None = text_problem(field, language, item.text)
        if problem is not None:
            raise ValidationFailedError(problem)

        if str(item.text) != code_text_of(field, language):
            entries.append(
                NicheTextEntry(
                    field_key=item.field_key, language=language, text=item.text
                )
            )

    return entries


def still_valid_entries(
    catalog: NicheTextCatalog, entries: Sequence[NicheTextEntry]
) -> list[NicheTextEntry]:
    """
    The entries the current code template still accepts (an earlier
    version may name a field or a placeholder the code has since dropped).
    """

    fields: dict[NicheTextFieldKey, NicheTextField] = {
        field.field_key: field for field in catalog.fields
    }
    kept: list[NicheTextEntry] = []
    for entry in entries:
        field: NicheTextField | None = fields.get(entry.field_key)
        if (
            field is not None
            and entry.language in EDITABLE_LANGUAGES
            and text_problem(field, entry.language, entry.text) is None
        ):
            kept.append(entry)

    return kept


def text_problem(
    field: NicheTextField, language: LanguageTag, text: NicheOverrideText
) -> str | None:
    """Why the wording does not fit the field (None: it fits)."""

    if len(text) > int(field.max_length):
        return (
            f"{field.field_key} takes at most {int(field.max_length)} characters "
            f"({len(text)} given)."
        )

    expected: frozenset[str] = placeholders(code_text_of(field, language))
    if placeholders(str(text)) != expected:
        named: str = ", ".join(f"{{{name}}}" for name in sorted(expected)) or "none"
        return (
            f"{field.field_key} must keep the placeholders of the code's text: {named}."
        )

    return None


def code_text_of(field: NicheTextField, language: LanguageTag) -> str:
    """The code's text in `language`, else the English one owners would read."""

    values = field.code_texts.values
    return str(values.get(language, values[FALLBACK_LANGUAGE_TAG]))


def placeholders(text: str) -> frozenset[str]:
    return frozenset(PLACEHOLDER_PATTERN.findall(text))
