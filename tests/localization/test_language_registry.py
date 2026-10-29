import pytest

from app.contracts.registries import LanguageRegistryContract
from app.registries.localization.language_registry import LanguageRegistry
from app.schemas.constants.localization import (
    LanguageTextSupport,
    LanguageVoiceSupport,
    TextDirection,
)
from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    ScriptCode,
)
from tests.localization.builders import get_language_registry

REGISTRY: LanguageRegistryContract = get_language_registry()


@pytest.mark.parametrize(
    ("tag", "english_name", "native_name", "script", "direction"),
    [
        ("ka", "Georgian", "ქართული", "Geor", TextDirection.LEFT_TO_RIGHT),
        ("ru", "Russian", "русский", "Cyrl", TextDirection.LEFT_TO_RIGHT),
        ("hy", "Armenian", "հայերեն", "Armn", TextDirection.LEFT_TO_RIGHT),
        ("he", "Hebrew", "עברית", "Hebr", TextDirection.RIGHT_TO_LEFT),
        ("ar", "Arabic", "العربية", "Arab", TextDirection.RIGHT_TO_LEFT),
        ("fa", "Persian", "فارسی", "Arab", TextDirection.RIGHT_TO_LEFT),
        ("ur", "Urdu", "اردو", "Arab", TextDirection.RIGHT_TO_LEFT),
        ("yi", "Yiddish", "ייִדיש", "Hebr", TextDirection.RIGHT_TO_LEFT),
        ("dv", "Divehi", "ދިވެހިބަސް", "Thaa", TextDirection.RIGHT_TO_LEFT),
        (
            "ckb",
            "Central Kurdish",
            "کوردیی ناوەندی",
            "Arab",
            TextDirection.RIGHT_TO_LEFT,
        ),
        ("ja", "Japanese", "日本語", "Jpan", TextDirection.LEFT_TO_RIGHT),
        (
            "pt-BR",
            "Portuguese (Brazil)",
            "português (Brasil)",
            "Latn",
            TextDirection.LEFT_TO_RIGHT,
        ),
        (
            "zh-Hant",
            "Chinese (Traditional)",
            "中文 (繁體)",
            "Hant",
            TextDirection.LEFT_TO_RIGHT,
        ),
        (
            "ru-GE",
            "Russian (Georgia)",
            "русский (Грузия)",
            "Cyrl",
            TextDirection.LEFT_TO_RIGHT,
        ),
        (
            "pa-PK",
            "Punjabi (Pakistan)",
            "پنجابی (پاکستان)",
            "Arab",
            TextDirection.RIGHT_TO_LEFT,
        ),
    ],
)
def test_language_profiles_come_from_cldr(
    tag: str,
    english_name: str,
    native_name: str,
    script: str,
    direction: TextDirection,
) -> None:
    profile = REGISTRY.get(LanguageTag(tag))

    assert profile.tag == tag
    assert profile.english_name == english_name
    assert profile.native_name == native_name
    assert profile.script == script
    assert type(profile.script) is ScriptCode
    assert profile.direction is direction


@pytest.mark.parametrize(
    ("tag", "voice_support"),
    [
        ("en", LanguageVoiceSupport.VERIFIED),
        ("ru", LanguageVoiceSupport.VERIFIED),
        ("es", LanguageVoiceSupport.VERIFIED),
        ("de", LanguageVoiceSupport.VERIFIED),
        ("fr", LanguageVoiceSupport.VERIFIED),
        ("it", LanguageVoiceSupport.VERIFIED),
        ("pt-BR", LanguageVoiceSupport.VERIFIED),
        ("tr", LanguageVoiceSupport.BETA),
        ("uk", LanguageVoiceSupport.BETA),
        ("pl", LanguageVoiceSupport.BETA),
        ("nl", LanguageVoiceSupport.BETA),
        ("ar", LanguageVoiceSupport.BETA),
        ("he", LanguageVoiceSupport.BETA),
        ("zh-Hant", LanguageVoiceSupport.BETA),
        ("ja", LanguageVoiceSupport.BETA),
        ("ko", LanguageVoiceSupport.BETA),
        ("hi", LanguageVoiceSupport.BETA),
        ("ka", LanguageVoiceSupport.NEEDS_PILOT_CHECK),
        ("hy", LanguageVoiceSupport.NEEDS_PILOT_CHECK),
        ("az", LanguageVoiceSupport.NEEDS_PILOT_CHECK),
        ("kk", LanguageVoiceSupport.NEEDS_PILOT_CHECK),
        ("sw", LanguageVoiceSupport.NEEDS_PILOT_CHECK),
        ("lt", LanguageVoiceSupport.NEEDS_PILOT_CHECK),
    ],
)
def test_voice_support_is_honest(tag: str, voice_support: LanguageVoiceSupport) -> None:
    assert REGISTRY.get(LanguageTag(tag)).voice_support is voice_support


def test_georgian_chat_is_supported_and_rare_languages_are_beta() -> None:
    assert REGISTRY.get(LanguageTag("ka")).text_support is LanguageTextSupport.SUPPORTED
    assert REGISTRY.get(LanguageTag("he")).text_support is LanguageTextSupport.SUPPORTED
    assert REGISTRY.get(LanguageTag("dv")).text_support is LanguageTextSupport.BETA
    assert REGISTRY.get(LanguageTag("xmf")).text_support is LanguageTextSupport.BETA


def test_language_without_locale_data_uses_english_name_natively() -> None:
    mingrelian = REGISTRY.get(LanguageTag("xmf"))

    assert mingrelian.english_name == "Mingrelian"
    assert mingrelian.native_name == "Mingrelian"


@pytest.mark.parametrize("tag", ["xx", "und", "zxx", "en-ZZ", "en-QQ", "ka-Zzzz"])
def test_unknown_tags_are_unsupported(tag: str) -> None:
    with pytest.raises(UnsupportedLanguageError):
        REGISTRY.get(LanguageTag(tag))


def test_list_all_is_sorted_and_covers_the_concept_languages() -> None:
    languages = REGISTRY.list_all()
    tags = [str(language.tag) for language in languages]

    assert tags == sorted(tags)
    assert len(tags) > 250
    for concept_language in ("ka", "ru", "en", "tr", "he", "ar", "hy", "kk", "pl"):
        assert concept_language in tags
    assert "zh-Hant" in tags
    assert "sr-Latn" in tags
    assert "eo" not in tags
    assert "la" not in tags
    assert "root" not in tags
    right_to_left = {
        str(language.tag)
        for language in languages
        if language.direction is TextDirection.RIGHT_TO_LEFT
    }
    assert {"ar", "he", "fa", "ur", "yi", "dv", "ps", "ckb"} <= right_to_left
    assert "ka" not in right_to_left


def test_profiles_are_cached_and_listing_is_a_new_list() -> None:
    registry = LanguageRegistry()
    first = registry.get(LanguageTag("ka"))

    assert registry.get(LanguageTag("ka")) is first
    listed = registry.list_all()
    listed.clear()
    assert registry.list_all() != []
