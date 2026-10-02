"""A shared country registry and short readers of its profiles."""

from app.contracts.registries import CountryRegistryContract
from app.schemas.dto.localization import CountryProfile
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from tests.localization.builders import (
    get_country_registry,
)

REGISTRY: CountryRegistryContract = get_country_registry()


def get_profile(country_code: str) -> CountryProfile:
    return REGISTRY.get(CountryCode(country_code))


def tags(language_tags: list[LanguageTag]) -> list[str]:
    return [str(language_tag) for language_tag in language_tags]
