"""
The six-step profile wizard as the cabinet shows it.

Display texts (labels, hints, titles) are resolved to one language for the
caller: requested tag, then its base language, then English.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import ProfileWizardStep
from app.schemas.dto.profiles.business_profile import BusinessProfileView
from app.schemas.dto.profiles.niche_catalog import (
    LocalizedQuestionView,
    NicheSummaryView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.schemas.typings.profiles.booleans import IsWizardStepComplete
from app.schemas.typings.profiles.constrained_integers import WizardStepNumber
from app.schemas.typings.profiles.constrained_strings import QuestionChoiceKey
from app.schemas.typings.profiles.strings import (
    ForbiddenRuleText,
    HandoffRuleText,
    ProfileAnswerText,
)


class ProfileWizardQuery(ImmutableDTO):
    """The wizard of a business in `language` (owner language when None)."""

    business_id: BusinessId
    language: LanguageTag | None = None


class WizardQuestionView(ImmutableDTO):
    """A niche question with the current answer."""

    question: LocalizedQuestionView
    answer: ProfileAnswerText | None = None
    selected_choice_keys: list[QuestionChoiceKey] = Field(
        default_factory=list[QuestionChoiceKey]
    )


class WizardStepView(ImmutableDTO):
    """
    One of the six wizard steps.

    `is_complete` means nothing required is missing in this step.
    """

    step: ProfileWizardStep
    number: WizardStepNumber
    title: LocalizedTextValue
    description: LocalizedTextValue
    questions: list[WizardQuestionView] = Field(
        default_factory=list[WizardQuestionView]
    )
    is_complete: IsWizardStepComplete


class ProfileWizardView(ImmutableDTO):
    """
    The six-step wizard (concept section 3) for one business.

    Country-dependent values (currency, time zone, customer languages) come
    from the business, so the same wizard works in any country.
    """

    business_id: BusinessId
    language: LanguageTag
    niche: NicheSummaryView
    country_code: CountryCode
    currency_code: CurrencyCode
    timezone: TimezoneName
    customer_languages: list[LanguageTag]
    default_language: LanguageTag
    knowledge_kinds: list[KnowledgeItemKind]
    default_handoff_rules: list[HandoffRuleText]
    default_forbidden_rules: list[ForbiddenRuleText]
    steps: list[WizardStepView]
    profile: BusinessProfileView
