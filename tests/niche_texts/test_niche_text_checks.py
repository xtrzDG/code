"""
An admin's wording is checked before it is stored: the field exists in the
code template, the language is the cabinet's, the text fits, keeps the
code's placeholders and holds no HTML or line break.
"""

import pytest
from base_typed_string import BaseTypedStringConstraintViolationError

from app.schemas.constants.niches import NicheKey, NicheTextSection
from app.schemas.domain.niche_texts import NicheTextEntry
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.niche_texts.niche_text_commands import NicheTextInput
from app.schemas.dto.niche_texts.niche_text_fields import (
    NicheTextCatalog,
    NicheTextField,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.schemas.typings.niches.constrained_integers import NicheTextLengthLimit
from app.schemas.typings.niches.constrained_strings import (
    NicheOverrideText,
    NicheTextFieldKey,
)
from app.utilities.niches.niche_text_checks import (
    check_draft_texts,
    still_valid_entries,
)

IT = LanguageTag("it")
GREETING = NicheTextFieldKey("starters.faq.greeting.answer")
LABEL = NicheTextFieldKey("questions.cuisine.label")


def field(
    key: NicheTextFieldKey, english: str, italian: str, limit: int
) -> NicheTextField:
    return NicheTextField(
        field_key=key,
        section=NicheTextSection.STARTERS,
        code_texts=LocalizedText(
            values={
                LanguageTag("en"): LocalizedTextValue(english),
                IT: LocalizedTextValue(italian),
            }
        ),
        max_length=NicheTextLengthLimit(limit),
    )


CATALOG = NicheTextCatalog(
    niche_key=NicheKey.RESTAURANT,
    fields=[
        field(GREETING, "Hello, {name}!", "Ciao, {name}!", 60),
        field(LABEL, "What cuisine do you serve?", "Che cucina proponi?", 30),
    ],
    questions=[],
)


def inputs(**texts: str) -> list[NicheTextInput]:
    keys = {"greeting": GREETING, "label": LABEL, "unknown": NicheTextFieldKey("x.y")}
    return [
        NicheTextInput(field_key=keys[name], text=NicheOverrideText(text))
        for name, text in texts.items()
    ]


def test_valid_texts_become_entries_of_their_language() -> None:
    entries = check_draft_texts(
        CATALOG, IT, inputs(greeting="Buongiorno, {name}!", label="La tua cucina?")
    )

    assert [(str(e.field_key), str(e.language), str(e.text)) for e in entries] == [
        (str(GREETING), "it", "Buongiorno, {name}!"),
        (str(LABEL), "it", "La tua cucina?"),
    ]


def test_the_codes_own_wording_overrides_nothing() -> None:
    assert check_draft_texts(CATALOG, IT, inputs(label="Che cucina proponi?")) == []


@pytest.mark.parametrize(
    ("language", "texts", "message"),
    [
        ("ru", {"label": "Какая кухня?"}, "cabinet's languages"),
        ("it", {"unknown": "Testo"}, "has no text x.y"),
        ("it", {"label": "Una domanda troppo lunga sulla cucina?"}, "at most 30"),
        ("it", {"greeting": "Buongiorno!"}, "placeholders of the code's text: {name}"),
        ("it", {"greeting": "Buongiorno, {name} e {city}!"}, "{name}"),
    ],
)
def test_a_text_that_does_not_fit_is_refused(
    language: str, texts: dict[str, str], message: str
) -> None:
    with pytest.raises(ValidationFailedError, match=message):
        check_draft_texts(CATALOG, LanguageTag(language), inputs(**texts))


def test_a_field_given_twice_is_refused() -> None:
    twice = [*inputs(label="Cucina?"), *inputs(label="La tua cucina?")]

    with pytest.raises(ValidationFailedError, match="given twice"):
        check_draft_texts(CATALOG, IT, twice)


@pytest.mark.parametrize(
    "text",
    [
        "<b>Кухня</b>",
        "Кухня <script>",
        "две\nстроки",
        " Кухня",
        "Кухня ",
        "",
        "x" * 1001,
    ],
)
def test_html_line_breaks_and_loose_spaces_never_become_a_text(text: str) -> None:
    with pytest.raises(BaseTypedStringConstraintViolationError):
        NicheOverrideText(text)


def test_a_comparison_sign_is_not_html() -> None:
    assert str(NicheOverrideText("Группы > 20 человек, дети < 3 лет")).startswith(
        "Группы"
    )


def test_an_older_versions_entries_are_kept_only_while_the_code_accepts_them() -> None:
    kept = NicheTextEntry(
        field_key=LABEL, language=IT, text=NicheOverrideText("Cucina?")
    )
    gone_field = NicheTextEntry(
        field_key=NicheTextFieldKey("questions.gone.label"),
        language=IT,
        text=NicheOverrideText("No"),
    )
    lost_placeholder = NicheTextEntry(
        field_key=GREETING, language=IT, text=NicheOverrideText("Ciao!")
    )
    other_language = NicheTextEntry(
        field_key=LABEL, language=LanguageTag("ru"), text=NicheOverrideText("Кухня?")
    )

    assert still_valid_entries(
        CATALOG, [kept, gone_field, lost_placeholder, other_language]
    ) == [kept]
