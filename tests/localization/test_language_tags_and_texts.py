import pytest

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.dto.localization import LocalizedText
from app.schemas.exceptions.application_errors import (
    UnsupportedLanguageError,
    ValidationFailedError,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.utilities.localization.babel_locales import (
    find_babel_locale,
    require_babel_locale,
)
from app.utilities.localization.cldr_language_names import is_known_language_tag
from app.utilities.localization.language_scripts import (
    find_likely_script_code,
    is_right_to_left_script,
)
from app.utilities.localization.language_tags import parse_language_tag
from app.utilities.localization.localized_text_resolver import (
    LocalizedTextResolver,
    build_lookup_chain,
)
from app.utilities.localization.localized_texts import build_localized_text

RESOLVER: LocalizedTextResolverContract = LocalizedTextResolver()


@pytest.mark.parametrize(
    ("raw_tag", "expected_tag"),
    [
        ("ka", "ka"),
        ("KA", "ka"),
        (" ru ", "ru"),
        ("pt_br", "pt-BR"),
        ("PT-br", "pt-BR"),
        ("zh-hant", "zh-Hant"),
        ("zh_HANT_tw", "zh-Hant-TW"),
        ("es-419", "es-419"),
        ("fil", "fil"),
    ],
)
def test_parse_language_tag_normalizes_case_and_separators(
    raw_tag: str,
    expected_tag: str,
) -> None:
    tag = parse_language_tag(raw_tag)

    assert tag == expected_tag
    assert type(tag) is LanguageTag


@pytest.mark.parametrize(
    "raw_tag",
    ["", "e", "english", "en-US-x-private", "ka-", "12", "en--US", "x" * 200],
)
def test_parse_language_tag_rejects_other_shapes(raw_tag: str) -> None:
    with pytest.raises(UnsupportedLanguageError):
        parse_language_tag(raw_tag)


@pytest.mark.parametrize(
    ("tag", "is_known"),
    [
        ("ka", True),
        ("he", True),
        ("pt-BR", True),
        ("ru-GE", True),
        ("sr-Latn-RS", True),
        ("es-419", True),
        ("xx", False),
        ("und", False),
        ("zxx", False),
        ("en-ZZ", False),
        ("en-Zzzz", False),
        ("en-QQ", False),
    ],
)
def test_known_language_tags_follow_cldr(tag: str, is_known: bool) -> None:
    assert is_known_language_tag(LanguageTag(tag)) is is_known


def test_babel_locale_falls_back_to_the_language() -> None:
    russian_in_georgia = find_babel_locale(LanguageTag("ru-GE"))
    brazilian_portuguese = find_babel_locale(LanguageTag("pt-BR"))

    assert russian_in_georgia is not None
    assert str(russian_in_georgia) == "ru"
    assert brazilian_portuguese is not None
    assert str(brazilian_portuguese) == "pt_BR"
    assert find_babel_locale(LanguageTag("xx")) is None
    with pytest.raises(UnsupportedLanguageError):
        require_babel_locale(LanguageTag("xx"))


@pytest.mark.parametrize(
    ("tag", "expected_script", "is_rtl"),
    [
        ("ka", "Geor", False),
        ("hy", "Armn", False),
        ("ru", "Cyrl", False),
        ("he", "Hebr", True),
        ("ar", "Arab", True),
        ("fa", "Arab", True),
        ("ur", "Arab", True),
        ("yi", "Hebr", True),
        ("dv", "Thaa", True),
        ("pa", "Guru", False),
        ("pa-PK", "Arab", True),
        ("zh", "Hans", False),
        ("zh-TW", "Hant", False),
        ("sr-Latn", "Latn", False),
        ("az-Arab", "Arab", True),
    ],
)
def test_likely_script_and_direction(
    tag: str, expected_script: str, is_rtl: bool
) -> None:
    script = find_likely_script_code(LanguageTag(tag))

    assert script == expected_script
    assert is_right_to_left_script(script) is is_rtl


def test_lookup_chain_drops_trailing_subtags() -> None:
    assert build_lookup_chain("zh-Hant-TW") == ["zh-Hant-TW", "zh-Hant", "zh"]
    assert build_lookup_chain("ka") == ["ka"]


GREETING: LocalizedText = build_localized_text(
    en="Hello",
    ru="Здравствуйте",
    ka="გამარჯობა",
    pt_PT="Olá (PT)",
    he="שלום",
)


@pytest.mark.parametrize(
    ("requested_tag", "expected_value"),
    [
        ("ka", "გამარჯობა"),
        ("ru-GE", "Здравствуйте"),
        ("he-IL", "שלום"),
        ("pt-PT", "Olá (PT)"),
        ("pt-BR", "Olá (PT)"),
        ("pt", "Olá (PT)"),
        ("de", "Hello"),
        ("en-GB", "Hello"),
    ],
)
def test_resolver_falls_back_tag_base_variant_english(
    requested_tag: str,
    expected_value: str,
) -> None:
    value = RESOLVER.resolve(GREETING, LanguageTag(requested_tag))

    assert value == expected_value
    assert type(value) is LocalizedTextValue


def test_resolver_prefers_base_language_over_sibling_variant() -> None:
    text = LocalizedText(
        values={
            LanguageTag("en"): LocalizedTextValue("Color"),
            LanguageTag("pt-PT"): LocalizedTextValue("Cor (PT)"),
            LanguageTag("pt"): LocalizedTextValue("Cor"),
        }
    )

    assert RESOLVER.resolve(text, LanguageTag("pt-BR")) == "Cor"


def test_resolver_uses_english_variant_then_any_value() -> None:
    british_only = LocalizedText(
        values={
            LanguageTag("ka"): LocalizedTextValue("ფერი"),
            LanguageTag("en-GB"): LocalizedTextValue("Colour"),
        }
    )
    georgian_only = LocalizedText(
        values={LanguageTag("ka"): LocalizedTextValue("ფერი")}
    )

    assert RESOLVER.resolve(british_only, LanguageTag("ja")) == "Colour"
    assert RESOLVER.resolve(georgian_only, LanguageTag("ja")) == "ფერი"


def test_resolver_rejects_empty_text() -> None:
    with pytest.raises(ValidationFailedError):
        RESOLVER.resolve(LocalizedText(values={}), LanguageTag("en"))


def test_localized_text_builder_requires_english() -> None:
    with pytest.raises(ValueError):
        build_localized_text(ka="გამარჯობა")
