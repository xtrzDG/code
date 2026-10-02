from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.booking_repositories import (
    UnansweredQuestionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.niches import ProfileWizardStep
from app.schemas.constants.profiles import ProfileGapKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.dto.niches import NicheTemplate, QuestionDefinition
from app.schemas.dto.profiles import (
    ProfileGap,
    ProfileGapFinding,
    ProfileGapsQuery,
    ProfileGapsView,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.assistants.strings import GapDescription
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.schemas.typings.profiles.constrained_strings import QuestionKey
from app.utilities.knowledge.profile_gaps import find_profile_gaps
from app.utilities.knowledge.profile_texts import GAP_TEXTS


class ComputeProfileGapsUseCase(UseCaseContract[ProfileGapsQuery, ProfileGapsView]):
    """
    Build the owner's "what to add" list (concept section 4).

    Lists what is missing in the profile (blocking items first) and then the
    customers' open unanswered questions with how often they were asked, most
    frequent first. Sandbox questions from owner tests and autotests are left
    out. Texts are in the requested language with English as the fallback.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        resource_repo: ResourceRepoContract,
        unanswered_question_repo: UnansweredQuestionRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        localized_text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._unanswered_question_repo: UnansweredQuestionRepoContract = (
            unanswered_question_repo
        )
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )

    def run(self, input_data: ProfileGapsQuery) -> ProfileGapsView:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        language: LanguageTag = input_data.language or business.owner_language
        template: NicheTemplate = self._niche_template_registry.get(business.niche_key)
        findings: list[ProfileGapFinding] = find_profile_gaps(
            template=template,
            business=business,
            profile=self._business_profile_repo.get_by_business(business.id),
            knowledge_items=self._knowledge_item_repo.list_by_business(business.id),
            resources=self._resource_repo.list_by_business(business.id),
        )
        questions_by_key: dict[QuestionKey, QuestionDefinition] = {
            question.key: question for question in template.questions
        }
        gaps: list[ProfileGap] = [
            ProfileGap(
                kind=finding.kind,
                step=finding.step,
                is_blocking=finding.is_blocking,
                description=self._describe(
                    finding,
                    template,
                    questions_by_key,
                    language,
                ),
                question_key=finding.question_key,
            )
            for finding in findings
        ]
        gaps.extend(self._unanswered_question_gaps(business, language))
        return ProfileGapsView(
            business_id=business.id,
            language=language,
            gaps=gaps,
            is_ready_for_assembly=not any(gap.is_blocking for gap in gaps),
        )

    def _describe(
        self,
        finding: ProfileGapFinding,
        template: NicheTemplate,
        questions_by_key: dict[QuestionKey, QuestionDefinition],
        language: LanguageTag,
    ) -> GapDescription:
        text: LocalizedTextValue = self._localized_text_resolver.resolve(
            GAP_TEXTS[finding.kind],
            language,
        )
        label: str = ""
        if finding.question_key is not None:
            label = self._localized_text_resolver.resolve(
                questions_by_key[finding.question_key].labels,
                language,
            )

        noun: LocalizedTextValue = self._localized_text_resolver.resolve(
            template.resource_nouns,
            language,
        )
        return GapDescription(text.format(label=label, noun=noun))

    def _unanswered_question_gaps(
        self,
        business: BusinessDocument,
        language: LanguageTag,
    ) -> list[ProfileGap]:
        open_questions: list[UnansweredQuestionDocument] = [
            question
            for question in self._unanswered_question_repo.list_by_business(business.id)
            if not question.is_resolved and not question.is_sandbox
        ]
        open_questions.sort(
            key=lambda question: (-question.occurrence_count, -question.last_seen_at)
        )
        text: LocalizedTextValue = self._localized_text_resolver.resolve(
            GAP_TEXTS[ProfileGapKind.UNANSWERED_QUESTION],
            language,
        )
        return [
            ProfileGap(
                kind=ProfileGapKind.UNANSWERED_QUESTION,
                step=ProfileWizardStep.FAQ_AND_HANDOFF,
                is_blocking=False,
                description=GapDescription(
                    text.format(
                        question=question.question,
                        count=int(question.occurrence_count),
                    )
                ),
                unanswered_question_id=question.id,
                unanswered_question=question.question,
                occurrence_count=question.occurrence_count,
            )
            for question in open_questions
        ]
