"""The languages CLDR lists for a territory, most spoken first."""

from collections.abc import Mapping
from typing import NamedTuple, cast

from babel.core import get_global

from app.schemas.typings.localization.constrained_strings import LanguageTag

OFFICIAL_LANGUAGE_STATUSES: frozenset[str] = frozenset(
    {"official", "de_facto_official"}
)


class TerritoryLanguage(NamedTuple):
    """One CLDR language of a territory (a technical record of Babel data)."""

    language_tag: LanguageTag
    population_percent: float
    is_official: bool


def load_territory_languages(region_code: str) -> list[TerritoryLanguage]:
    """CLDR languages of a territory, most spoken first."""

    raw_languages: object = get_global("territory_languages").get(region_code)
    if not isinstance(raw_languages, Mapping):
        return []

    territory_languages: list[TerritoryLanguage] = []
    for raw_language_code, raw_details in cast(
        Mapping[object, object],
        raw_languages,
    ).items():
        if not isinstance(raw_language_code, str) or not isinstance(
            raw_details,
            Mapping,
        ):
            continue

        details: Mapping[object, object] = cast(Mapping[object, object], raw_details)
        try:
            language_tag = LanguageTag(raw_language_code.replace("_", "-"))
        except ValueError:
            continue

        population_percent: object = details.get("population_percent")
        territory_languages.append(
            TerritoryLanguage(
                language_tag=language_tag,
                population_percent=(
                    float(population_percent)
                    if isinstance(population_percent, int | float)
                    else 0.0
                ),
                is_official=details.get("official_status")
                in OFFICIAL_LANGUAGE_STATUSES,
            )
        )

    return sorted(
        territory_languages,
        key=lambda territory_language: -territory_language.population_percent,
    )
