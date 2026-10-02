from babel import Locale, UnknownLocaleError

from app.contracts.starter_registries import StarterAnswerRegistryContract
from app.registries.niches.starters.starter_catalog import NICHE_STARTERS
from app.schemas.constants.businesses import Weekday
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.dto.setup.starter_catalog import (
    NicheStarterDefinition,
    StarterAnswers,
    StarterOpening,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.localization.constrained_strings import CountryCode

# CLDR numbers weekdays from Monday = 0; the profile from Monday = 1.
CLDR_WEEKDAY_OFFSET: int = 1
DAYS_PER_WEEK: int = 7
# Most of the world rests on Saturday and Sunday; used when CLDR does not
# know the country.
DEFAULT_WEEKEND: frozenset[Weekday] = frozenset({Weekday.SATURDAY, Weekday.SUNDAY})


class StarterAnswerRegistry(StarterAnswerRegistryContract):
    """
    The starter answers of all sixteen niches, laid over the working week
    of the business's country: CLDR knows that Israel rests on Friday and
    Saturday, Iran on Friday, India on Sunday. Definitions are checked once
    (one per niche) and returned as immutable DTOs.
    """

    def __init__(self) -> None:
        starters_by_key: dict[NicheKey, NicheStarterDefinition] = {}
        for definition in NICHE_STARTERS:
            if definition.niche_key in starters_by_key:
                raise ValueError(f"Niche {definition.niche_key} has two starters.")

            starters_by_key[definition.niche_key] = definition

        missing_keys: list[NicheKey] = [
            niche_key for niche_key in NicheKey if niche_key not in starters_by_key
        ]
        if missing_keys != []:
            raise ValueError(f"Niches without starter answers: {missing_keys}.")

        self._starters_by_key: dict[NicheKey, NicheStarterDefinition] = starters_by_key
        self._weekends_by_country: dict[CountryCode, frozenset[Weekday]] = {}

    def get(self, niche_key: NicheKey, country_code: CountryCode) -> StarterAnswers:
        definition: NicheStarterDefinition | None = self._starters_by_key.get(
            niche_key
        )
        if definition is None:
            raise NotFoundError(f"Niche {niche_key} has no starter answers.")

        return StarterAnswers(
            niche_key=definition.niche_key,
            hours=lay_over_week(definition.opening, self._weekend_of(country_code)),
            booking=definition.booking,
            resource=definition.resource,
            tones=definition.tones,
            faq=list(definition.faq),
            offers=list(definition.offers),
        )

    def _weekend_of(self, country_code: CountryCode) -> frozenset[Weekday]:
        weekend: frozenset[Weekday] | None = self._weekends_by_country.get(
            country_code
        )
        if weekend is None:
            weekend = find_weekend(country_code)
            self._weekends_by_country[country_code] = weekend

        return weekend


def find_weekend(country_code: CountryCode) -> frozenset[Weekday]:
    """The country's weekend days from CLDR (Saturday and Sunday if unknown)."""

    try:
        locale: Locale = Locale.parse(f"und_{country_code}")
    except (UnknownLocaleError, ValueError):
        return DEFAULT_WEEKEND

    start: int = locale.weekend_start
    end: int = locale.weekend_end
    length: int = (end - start) % DAYS_PER_WEEK + 1
    return frozenset(
        Weekday((start + offset) % DAYS_PER_WEEK + CLDR_WEEKDAY_OFFSET)
        for offset in range(length)
    )


def lay_over_week(
    opening: StarterOpening,
    weekend: frozenset[Weekday],
) -> list[OpeningInterval]:
    """Opening intervals Monday to Sunday: working-day or weekend hours."""

    intervals: list[OpeningInterval] = []
    for weekday in Weekday:
        if weekday not in weekend:
            intervals.append(
                OpeningInterval(
                    weekday=weekday,
                    opens_at=opening.workday_opens_at,
                    closes_at=opening.workday_closes_at,
                )
            )
        elif opening.weekend_opens_at is not None and (
            opening.weekend_closes_at is not None
        ):
            intervals.append(
                OpeningInterval(
                    weekday=weekday,
                    opens_at=opening.weekend_opens_at,
                    closes_at=opening.weekend_closes_at,
                )
            )

    return intervals
