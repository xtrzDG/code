from app.contracts.repositories.niche_text_repositories import NicheTextRepoContract
from app.contracts.starter_registries import StarterAnswerRegistryContract
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.setup.starter_catalog import StarterAnswers
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.utilities.niches.niche_text_overlay import overlay_starter_answers


class EffectiveStarterAnswerRegistry(StarterAnswerRegistryContract):
    """
    The starter answers a new owner is offered: the code's suggestions
    with the texts of the niche's newest published version laid over them
    (tone, cancellation rule, first resource, frequent questions and
    answers, offer examples). Hours and every number stay as in code.
    """

    def __init__(
        self,
        code_starters: StarterAnswerRegistryContract,
        niche_text_repo: NicheTextRepoContract,
    ) -> None:
        self._code_starters: StarterAnswerRegistryContract = code_starters
        self._niche_text_repo: NicheTextRepoContract = niche_text_repo

    def get(self, niche_key: NicheKey, country_code: CountryCode) -> StarterAnswers:
        starters: StarterAnswers = self._code_starters.get(niche_key, country_code)
        for release in self._niche_text_repo.latest_releases([niche_key]):
            return overlay_starter_answers(starters, release.entries)

        return starters
