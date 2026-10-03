from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.profiles.niche_catalog import NicheCatalogQuery, NicheCatalogView
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.knowledge.localized_texts import FALLBACK_LANGUAGE_TAG
from app.utilities.knowledge.niche_views import to_niche_summary


class ListNicheTemplatesUseCase(UseCaseContract[NicheCatalogQuery, NicheCatalogView]):
    """
    List every niche the platform supports, in the requested language.

    Used before sign-up, so it needs no business; English is the fallback
    when no language is given.
    """

    def __init__(
        self,
        niche_template_registry: NicheTemplateRegistryContract,
        localized_text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )

    def run(self, input_data: NicheCatalogQuery) -> NicheCatalogView:
        language: LanguageTag = input_data.language or FALLBACK_LANGUAGE_TAG
        return NicheCatalogView(
            language=language,
            niches=[
                to_niche_summary(template, language, self._localized_text_resolver)
                for template in self._niche_template_registry.list_all()
            ],
        )
