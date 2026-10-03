"""Contract of the niche starter answers (suggestions for a new business)."""

from typing import Protocol

from app.contracts.registry_contract import RegistryContract
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.setup.starter_catalog import StarterAnswers
from app.schemas.typings.localization.constrained_strings import CountryCode


class StarterAnswerRegistryContract(RegistryContract, Protocol):
    def get(self, niche_key: NicheKey, country_code: CountryCode) -> StarterAnswers:
        """
        The starter answers of a niche for a business in a country: typical
        hours laid over that country's working week (its weekend from
        CLDR), booking rules, a first resource, tone, frequent questions and
        offer examples.
        """
        raise NotImplementedError
