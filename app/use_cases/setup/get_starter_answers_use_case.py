from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.starter_registries import StarterAnswerRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.knowledge_admin import KnowledgeItemUpsertInput
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.setup.starter_answers import (
    StarterAnswersQuery,
    StarterAnswersView,
    StarterFaqView,
)
from app.schemas.dto.setup.starter_catalog import StarterAnswers
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.knowledge.niche_views import (
    default_forbidden_rules,
    default_handoff_rules,
)
from app.utilities.setup.starter_views import (
    booking_rules_input,
    faq_views,
    missing_faq_inputs,
    offer_views,
    offered_sections,
    resource_input,
    resource_view,
    section_views,
    tone,
)


class GetStarterAnswersUseCase(
    UseCaseContract[StarterAnswersQuery, StarterAnswersView]
):
    """
    The niche's starter answers for one business, in the owner's language
    (or the one asked for): typical hours over the country's working week,
    booking rules and a first resource (niches that take bookings), handoff
    and forbidden rules, a tone, frequent questions and offer examples.

    They are suggestions only; nothing is saved. Each section says whether
    the profile still lacks it (applying would fill it) or the owner has
    already filled it (applying keeps the owner's version). Offer examples
    carry no price: prices only ever come from the owner.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        business_profile_repo: BusinessProfileRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        resource_repo: ResourceRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        starter_answer_registry: StarterAnswerRegistryContract,
        localized_text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._starter_answer_registry: StarterAnswerRegistryContract = (
            starter_answer_registry
        )
        self._resolver: LocalizedTextResolverContract = localized_text_resolver

    def run(self, input_data: StarterAnswersQuery) -> StarterAnswersView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        language: LanguageTag = input_data.language or business.owner_language
        template: NicheTemplate = self._niche_template_registry.get(business.niche_key)
        starters: StarterAnswers = self._starter_answer_registry.get(
            business.niche_key, business.country_code
        )
        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        resources: list[ResourceDocument] = self._resource_repo.list_by_business(
            business.id
        )
        knowledge_items: list[KnowledgeItemDocument] = (
            self._knowledge_item_repo.list_by_business(business.id)
        )
        faq: list[StarterFaqView] = faq_views(starters, language, self._resolver)
        missing_faq: list[KnowledgeItemUpsertInput] = missing_faq_inputs(
            faq, knowledge_items, language
        )
        return StarterAnswersView(
            business_id=business.id,
            niche_key=business.niche_key,
            language=language,
            sections=section_views(
                offered_sections(template, starters),
                profile,
                resources,
                missing_faq,
            ),
            hours=list(starters.hours),
            booking_rules=booking_rules_input(
                template, starters, language, self._resolver
            ),
            resource=resource_view(
                template,
                resource_input(template, starters, language, self._resolver),
            ),
            handoff_rules=default_handoff_rules(template, language, self._resolver),
            forbidden_rules=default_forbidden_rules(template, language, self._resolver),
            tone=tone(starters, language, self._resolver),
            faq=faq,
            offer_examples=offer_views(starters, language, self._resolver),
        )
