import re
import threading

from babel import Locale

from app.contracts.registries import LanguageRegistryContract
from app.registries.localization.language_support_data import (
    DEFAULT_VOICE_SUPPORT,
    EXTRA_LISTED_LANGUAGES,
    TEXT_SUPPORTED_LANGUAGES,
    UNLISTED_LANGUAGES,
    VOICE_SUPPORT_BY_LANGUAGE,
)
from app.schemas.constants.localization import (
    LanguageTextSupport,
    LanguageVoiceSupport,
    TextDirection,
)
from app.schemas.dto.localization import LanguageProfile
from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    ScriptCode,
)
from app.schemas.typings.localization.strings import LanguageDisplayName
from app.utilities.localization.babel_locales import (
    find_babel_locale,
    load_locale_identifiers,
)
from app.utilities.localization.cldr_language_names import (
    get_english_locale,
    is_known_language_tag,
    require_known_language_tag,
)
from app.utilities.localization.display_names import build_language_display_name
from app.utilities.localization.language_scripts import (
    find_likely_script_code,
    is_right_to_left_script,
)
from app.utilities.localization.language_tags import LanguageTagParts

BARE_LANGUAGE_IDENTIFIER_PATTERN: re.Pattern[str] = re.compile(r"^[a-z]{2,3}$")
# Tags may come from requests; past this many, profiles are built uncached.
MAX_CACHED_PROFILES: int = 4096


class LanguageRegistry(LanguageRegistryContract):
    """
    Every language CLDR knows, as BCP 47 tags with optional script and region.

    Names, scripts (CLDR likely subtags) and writing direction come from
    Babel; text and voice support levels are curated
    (`language_support_data`). `list_all` lists the bare languages with CLDR
    locale data plus common script variants; `get` accepts any known tag such
    as "pt-BR" or "ru-GE". Profiles are built once and cached.
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._profiles_by_tag: dict[str, LanguageProfile] = {}
        self._listed_profiles: list[LanguageProfile] | None = None

    def get(self, language_tag: LanguageTag) -> LanguageProfile:
        with self._lock:
            cached_profile: LanguageProfile | None = self._profiles_by_tag.get(
                str(language_tag)
            )

        if cached_profile is not None:
            return cached_profile

        profile: LanguageProfile = build_language_profile(language_tag)
        with self._lock:
            if len(self._profiles_by_tag) < MAX_CACHED_PROFILES:
                self._profiles_by_tag[str(language_tag)] = profile

        return profile

    def list_all(self) -> list[LanguageProfile]:
        with self._lock:
            listed_profiles: list[LanguageProfile] | None = self._listed_profiles

        if listed_profiles is None:
            listed_profiles = [
                self.get(language_tag) for language_tag in list_catalog_language_tags()
            ]
            with self._lock:
                self._listed_profiles = listed_profiles

        return list(listed_profiles)


def build_language_profile(language_tag: LanguageTag) -> LanguageProfile:
    """
    Raises:
        UnsupportedLanguageError: CLDR does not know the tag.
    """

    parts: LanguageTagParts = require_known_language_tag(language_tag)
    english_name: LanguageDisplayName | None = build_language_display_name(
        language_tag,
        get_english_locale(),
    )
    if english_name is None:
        raise UnsupportedLanguageError(f"Language {language_tag} is not known.")

    native_locale: Locale | None = find_babel_locale(language_tag)
    native_name: LanguageDisplayName | None = None
    if native_locale is not None:
        native_name = build_language_display_name(language_tag, native_locale)

    script_code: str = find_likely_script_code(language_tag)
    return LanguageProfile(
        tag=language_tag,
        english_name=english_name,
        native_name=native_name if native_name is not None else english_name,
        script=ScriptCode(script_code),
        direction=(
            TextDirection.RIGHT_TO_LEFT
            if is_right_to_left_script(script_code)
            else TextDirection.LEFT_TO_RIGHT
        ),
        text_support=(
            LanguageTextSupport.SUPPORTED
            if parts.language in TEXT_SUPPORTED_LANGUAGES
            else LanguageTextSupport.BETA
        ),
        voice_support=find_voice_support(parts.language),
    )


def find_voice_support(language_code: str) -> LanguageVoiceSupport:
    for supported_language, voice_support in VOICE_SUPPORT_BY_LANGUAGE.items():
        if supported_language == language_code:
            return voice_support

    return DEFAULT_VOICE_SUPPORT


def list_catalog_language_tags() -> list[LanguageTag]:
    """Bare languages with CLDR locale data, minus unlisted ones, plus extras."""

    language_tags: dict[str, LanguageTag] = {}
    for locale_identifier in load_locale_identifiers():
        if BARE_LANGUAGE_IDENTIFIER_PATTERN.fullmatch(locale_identifier) is None:
            continue

        language_tag = LanguageTag(locale_identifier)
        if language_tag in UNLISTED_LANGUAGES or not is_known_language_tag(
            language_tag
        ):
            continue

        language_tags[locale_identifier] = language_tag

    for extra_language_tag in EXTRA_LISTED_LANGUAGES:
        language_tags[str(extra_language_tag)] = extra_language_tag

    return [language_tags[tag_text] for tag_text in sorted(language_tags)]
