"""
The languages of the language autotests (concept section 11).

A customer may write a language the business did not list, or a business
language in Latin letters; the assistant must answer, and the platform must
put the AI disclosure, in that language. The foreign-language scenarios use
a language whose script no business language uses (so the replies and the
disclosure can be checked by script) and a Latin-script language the
business does not list (so the detection among Latin languages is
exercised). The transliteration scenarios use the business languages often
typed in Latin letters (Georgian, Russian, Ukrainian, Armenian, Hebrew).
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.language_evidence.transliterated_languages import (
    TRANSLITERATED_LANGUAGE_EVIDENCE,
)
from app.utilities.conversations.language_scoring import evidence_code
from app.utilities.localization.language_scripts import find_likely_script_code

LANGUAGE_SCENARIO_KINDS: frozenset[AutotestScenarioKind] = frozenset(
    {
        AutotestScenarioKind.FOREIGN_LANGUAGE,
        AutotestScenarioKind.TRANSLITERATED,
    }
)
# Foreign languages written in a script of their own, in order of preference.
OWN_SCRIPT_PROBE_LANGUAGES: tuple[str, ...] = (
    "he",
    "ar",
    "hy",
    "el",
    "ka",
    "ru",
    "th",
    "ko",
    "ja",
)
# Foreign languages written in the Latin script, in order of preference.
LATIN_PROBE_LANGUAGES: tuple[str, ...] = ("de", "fr", "es", "tr", "it", "pl", "en")


def choose_foreign_languages(
    business_languages: Sequence[LanguageTag],
) -> list[LanguageTag]:
    """
    One language in a script no business language uses, then one Latin-script
    language the business does not list.
    """

    codes: set[str] = {evidence_code(language) for language in business_languages}
    scripts: set[str] = {
        find_likely_script_code(language) for language in business_languages
    }
    own_script: list[LanguageTag] = [
        LanguageTag(code)
        for code in OWN_SCRIPT_PROBE_LANGUAGES
        if code not in codes
        and find_likely_script_code(LanguageTag(code)) not in scripts
    ]
    latin: list[LanguageTag] = [
        LanguageTag(code) for code in LATIN_PROBE_LANGUAGES if code not in codes
    ]
    return own_script[:1] + latin[:1]


def choose_transliterated_languages(
    languages: Sequence[LanguageTag],
) -> list[LanguageTag]:
    """The languages customers often type in Latin letters, in their order."""

    return [
        language
        for language in languages
        if evidence_code(language) in TRANSLITERATED_LANGUAGE_EVIDENCE
    ]
