from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import (
    LaunchWave,
    NicheKey,
    ProfileWizardStep,
    QuestionAnswerType,
)
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.assistants.strings import PromptRuleText
from app.schemas.typings.niches.booleans import (
    IsQuestionRequired,
    RequiresLegalReview,
    TakesBookings,
)
from app.schemas.typings.niches.strings import IntegrationName
from app.schemas.typings.profiles.constrained_strings import (
    FactKey,
    QuestionChoiceKey,
    QuestionKey,
)


class QuestionChoice(ImmutableDTO):
    """Predefined answer of a choice question."""

    key: QuestionChoiceKey
    labels: LocalizedText


class QuestionDefinition(ImmutableDTO):
    """A niche-specific profile question; its answer becomes fact `fact_key`."""

    key: QuestionKey
    step: ProfileWizardStep
    answer_type: QuestionAnswerType
    is_required: IsQuestionRequired
    labels: LocalizedText
    hints: LocalizedText | None = None
    choices: list[QuestionChoice] = Field(default_factory=list[QuestionChoice])
    fact_key: FactKey


class NicheTemplate(ImmutableDTO):
    """
    Everything a niche changes: profile questions, what is booked, and the
    rules for passing to a human (concept "Одна платформа для всех ниш").

    Prompt rules are English text for the language model; the assistant still
    answers customers in their language. Default handoff and forbidden rules
    are localized for the owner, one rule per line, and pre-fill the profile.

    `takes_bookings` is False for niches that only take orders as leads
    (online shops, B2B supply); their resource kind and booking unit are then
    unused.
    """

    key: NicheKey
    wave: LaunchWave
    names: LocalizedText
    descriptions: LocalizedText
    recommended_plans: list[PlanKey]
    resource_kind: ResourceKind
    booking_unit: BookingUnit
    takes_bookings: TakesBookings = True
    resource_nouns: LocalizedText
    knowledge_kinds: list[KnowledgeItemKind]
    questions: list[QuestionDefinition]
    prompt_rules: list[PromptRuleText]
    default_handoff_rules: LocalizedText
    default_forbidden_rules: LocalizedText
    autotest_kinds: list[AutotestScenarioKind]
    integrations: list[IntegrationName] = Field(default_factory=list[IntegrationName])
    requires_legal_review: RequiresLegalReview = False
