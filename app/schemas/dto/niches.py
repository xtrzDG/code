from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.handoffs import HandoffReason
from app.schemas.constants.niches import (
    BookableResourceKind,
    LaunchWave,
    NicheKey,
    QuestionAnswerType,
    QuestionnaireSection,
)
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.assistants.strings import PromptRuleText
from app.schemas.typings.niches.booleans import (
    IsQuestionRequired,
    RequiresLegalReview,
)
from app.schemas.typings.niches.strings import IntegrationName
from app.schemas.typings.questionnaires.constrained_strings import (
    FactKey,
    QuestionChoiceKey,
    QuestionKey,
)


class QuestionChoice(ImmutableDTO):
    """Predefined answer of a choice question."""

    key: QuestionChoiceKey
    labels: LocalizedText


class QuestionDefinition(ImmutableDTO):
    """One questionnaire question; its answer becomes the fact `fact_key`."""

    key: QuestionKey
    section: QuestionnaireSection
    answer_type: QuestionAnswerType
    is_required: IsQuestionRequired
    labels: LocalizedText
    hints: LocalizedText | None = None
    choices: list[QuestionChoice] = Field(default_factory=list[QuestionChoice])
    fact_key: FactKey


class NicheTemplate(ImmutableDTO):
    """
    Everything a niche changes: questions, what is booked, handoff rules.

    Prompt rules are written in English for the language model; the assistant
    still answers customers in their own language.
    """

    key: NicheKey
    wave: LaunchWave
    names: LocalizedText
    descriptions: LocalizedText
    recommended_plans: list[PlanKey]
    resource_kind: BookableResourceKind
    resource_nouns: LocalizedText
    questions: list[QuestionDefinition]
    handoff_reasons: list[HandoffReason]
    prompt_rules: list[PromptRuleText]
    autotest_kinds: list[AutotestScenarioKind]
    integrations: list[IntegrationName] = Field(default_factory=list[IntegrationName])
    requires_legal_review: RequiresLegalReview = False
