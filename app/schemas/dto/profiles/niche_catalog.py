"""
The niche catalog: niche templates with their localized questions.

Display texts (labels, hints, titles) are resolved to one language for the
caller: requested tag, then its base language, then English.
"""

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
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LocalizedTextValue
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
from app.schemas.typings.profiles.strings import ForbiddenRuleText, HandoffRuleText


class NicheCatalogQuery(ImmutableDTO):
    """List the niches with texts in `language` (English when None)."""

    language: LanguageTag | None = None


class NicheTemplateQuery(ImmutableDTO):
    """One niche with its questions in `language` (English when None)."""

    niche_key: NicheKey
    language: LanguageTag | None = None


class LocalizedChoiceView(ImmutableDTO):
    """A predefined answer with its label in one language."""

    key: QuestionChoiceKey
    label: LocalizedTextValue


class LocalizedQuestionView(ImmutableDTO):
    """A niche question with its texts in one language."""

    key: QuestionKey
    fact_key: FactKey
    step: ProfileWizardStep
    answer_type: QuestionAnswerType
    is_required: IsQuestionRequired
    label: LocalizedTextValue
    hint: LocalizedTextValue | None = None
    choices: list[LocalizedChoiceView] = Field(
        default_factory=list[LocalizedChoiceView]
    )


class NicheSummaryView(ImmutableDTO):
    """What a niche is and what it books, in one language."""

    key: NicheKey
    wave: LaunchWave
    name: LocalizedTextValue
    description: LocalizedTextValue
    recommended_plans: list[PlanKey]
    resource_kind: ResourceKind
    booking_unit: BookingUnit
    takes_bookings: TakesBookings
    resource_noun: LocalizedTextValue
    requires_legal_review: RequiresLegalReview
    integrations: list[IntegrationName] = Field(default_factory=list[IntegrationName])


class NicheCatalogView(ImmutableDTO):
    """Every niche the platform supports."""

    language: LanguageTag
    niches: list[NicheSummaryView]


class NicheDetailsView(ImmutableDTO):
    """
    A niche with everything the owner sees before signing up.

    Default handoff and forbidden rules pre-fill the profile; prompt rules
    stay internal to assistant assembly.
    """

    language: LanguageTag
    niche: NicheSummaryView
    knowledge_kinds: list[KnowledgeItemKind]
    questions: list[LocalizedQuestionView]
    default_handoff_rules: list[HandoffRuleText]
    default_forbidden_rules: list[ForbiddenRuleText]
    autotest_kinds: list[AutotestScenarioKind]
