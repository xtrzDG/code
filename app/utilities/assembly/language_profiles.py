"""Language profiles of the business languages, tolerant of unknown tags."""

from collections.abc import Sequence

from app.contracts.registries import LanguageRegistryContract
from app.schemas.dto.assistants.autotest_runs import AutotestLanguage
from app.schemas.dto.localization import LanguageProfile
from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LanguageDisplayName


def collect_language_profiles(
    language_registry: LanguageRegistryContract,
    language_tags: Sequence[LanguageTag],
) -> list[LanguageProfile]:
    """Profiles of the tags the registry knows; unknown tags are skipped."""

    profiles: list[LanguageProfile] = []
    for language_tag in language_tags:
        try:
            profiles.append(language_registry.get(language_tag))
        except UnsupportedLanguageError:
            continue

    return profiles


def build_autotest_languages(
    language_tags: Sequence[LanguageTag],
    language_profiles: Sequence[LanguageProfile],
) -> list[AutotestLanguage]:
    """
    Scenario languages with English names and scripts; a tag without a
    profile is named by itself and gets no script check.
    """

    profiles_by_tag: dict[str, LanguageProfile] = {
        str(profile.tag): profile for profile in language_profiles
    }
    languages: list[AutotestLanguage] = []
    for language_tag in language_tags:
        profile: LanguageProfile | None = profiles_by_tag.get(str(language_tag))
        languages.append(
            AutotestLanguage(
                tag=language_tag,
                name=(
                    profile.english_name
                    if profile is not None
                    else LanguageDisplayName(str(language_tag))
                ),
                script=profile.script if profile is not None else None,
            )
        )

    return languages
