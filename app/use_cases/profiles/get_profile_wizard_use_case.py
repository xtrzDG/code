from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.niches import ProfileWizardStep, QuestionAnswerType
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessProfileDocument, ProfileAnswer
from app.schemas.dto.niches import NicheTemplate, QuestionDefinition
from app.schemas.dto.profiles import (
    ProfileGapFinding,
    ProfileWizardQuery,
    ProfileWizardView,
    WizardQuestionView,
    WizardStepView,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.profiles.constrained_integers import WizardStepNumber
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey,
    QuestionKey,
)
from app.utilities.knowledge.niche_answers import split_choice_answer
from app.utilities.knowledge.niche_views import (
    default_forbidden_rules,
    default_handoff_rules,
    to_localized_question,
    to_niche_summary,
)
from app.utilities.knowledge.profile_gaps import blocking_steps, find_profile_gaps
from app.utilities.knowledge.profile_texts import (
    WIZARD_STEP_DESCRIPTIONS,
    WIZARD_STEP_ORDER,
    WIZARD_STEP_TITLES,
)
from app.utilities.knowledge.profile_views import to_profile_view

CHOICE_ANSWER_TYPES: frozenset[QuestionAnswerType] = frozenset(
    {
        QuestionAnswerType.SINGLE_CHOICE,
        QuestionAnswerType.MULTIPLE_CHOICE,
        QuestionAnswerType.YES_NO,
    }
)


class GetProfileWizardUseCase(UseCaseContract[ProfileWizardQuery, ProfileWizardView]):
    """
    Show the six-step profile wizard of a business (concept section 3).

    Niche questions, step texts and default rules are resolved to the
    requested language (the owner's language by default); the current
    answers and per-step completeness let the owner continue where they
    stopped.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        resource_repo: ResourceRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        localized_text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )

    def run(self, input_data: ProfileWizardQuery) -> ProfileWizardView:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        language: LanguageTag = input_data.language or business.owner_language
        template: NicheTemplate = self._niche_template_registry.get(business.niche_key)
        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        findings: list[ProfileGapFinding] = find_profile_gaps(
            template=template,
            business=business,
            profile=profile,
            knowledge_items=self._knowledge_item_repo.list_by_business(business.id),
            resources=self._resource_repo.list_by_business(business.id),
        )
        incomplete_steps: set[ProfileWizardStep] = blocking_steps(findings)
        answers_by_key: dict[QuestionKey, ProfileAnswer] = (
            {}
            if profile is None
            else {answer.question_key: answer for answer in profile.niche_answers}
        )
        resolver: LocalizedTextResolverContract = self._localized_text_resolver
        steps: list[WizardStepView] = []
        for position, step in enumerate(WIZARD_STEP_ORDER, start=1):
            steps.append(
                WizardStepView(
                    step=step,
                    number=WizardStepNumber(position),
                    title=resolver.resolve(WIZARD_STEP_TITLES[step], language),
                    description=resolver.resolve(
                        WIZARD_STEP_DESCRIPTIONS[step],
                        language,
                    ),
                    questions=[
                        self._question_view(
                            question,
                            answers_by_key.get(question.key),
                            language,
                        )
                        for question in template.questions
                        if question.step is step
                    ],
                    is_complete=step not in incomplete_steps,
                )
            )

        return ProfileWizardView(
            business_id=business.id,
            language=language,
            niche=to_niche_summary(template, language, resolver),
            country_code=business.country_code,
            currency_code=business.currency_code,
            timezone=business.timezone,
            customer_languages=list(business.languages),
            default_language=business.default_language,
            knowledge_kinds=list(template.knowledge_kinds),
            default_handoff_rules=default_handoff_rules(template, language, resolver),
            default_forbidden_rules=default_forbidden_rules(
                template,
                language,
                resolver,
            ),
            steps=steps,
            profile=to_profile_view(business, profile),
        )

    def _question_view(
        self,
        question: QuestionDefinition,
        answer: ProfileAnswer | None,
        language: LanguageTag,
    ) -> WizardQuestionView:
        selected_choice_keys: list[QuestionChoiceKey] = []
        if answer is not None and question.answer_type in CHOICE_ANSWER_TYPES:
            selected_choice_keys = split_choice_answer(answer.answer)

        return WizardQuestionView(
            question=to_localized_question(
                question,
                language,
                self._localized_text_resolver,
            ),
            answer=None if answer is None else answer.answer,
            selected_choice_keys=selected_choice_keys,
        )
