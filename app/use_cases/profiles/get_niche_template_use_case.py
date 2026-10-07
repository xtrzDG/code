from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.profiles.niche_catalog import NicheDetailsView, NicheTemplateQuery
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.knowledge.localized_texts import FALLBACK_LANGUAGE_TAG
from app.utilities.knowledge.niche_views import (
    default_forbidden_rules,
    default_handoff_rules,
    to_localized_question,
    to_niche_summary,
)


class GetNicheTemplateUseCase(UseCaseContract[NicheTemplateQuery, NicheDetailsView]):
    """
    Show one niche with its questions and default rules in one language.

    Prompt rules stay internal: they are instructions for the language model,
    not something the owner edits.
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

    def run(self, input_data: NicheTemplateQuery) -> NicheDetailsView:
        language: LanguageTag = input_data.language or FALLBACK_LANGUAGE_TAG
        template: NicheTemplate = self._niche_template_registry.get(
            input_data.niche_key
        )
        resolver: LocalizedTextResolverContract = self._localized_text_resolver
        return NicheDetailsView(
            language=language,
            niche=to_niche_summary(template, language, resolver),
            knowledge_kinds=list(template.knowledge_kinds),
            questions=[
                to_localized_question(question, language, resolver)
                for question in template.questions
            ],
            default_handoff_rules=default_handoff_rules(template, language, resolver),
            default_forbidden_rules=default_forbidden_rules(
                template,
                language,
                resolver,
            ),
            autotest_kinds=list(template.autotest_kinds),
        )
