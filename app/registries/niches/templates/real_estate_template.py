from app.registries.niches.examples.trade_examples import REAL_ESTATE_EXAMPLES
from app.registries.niches.template_parts import (
    autotest_kinds,
    forbidden_rules,
    handoff_rules,
    prompt_rules,
    question,
    text,
)
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import LaunchWave, NicheKey
from app.schemas.constants.niches import ProfileWizardStep as Step
from app.schemas.constants.niches import QuestionAnswerType as Answer
from app.schemas.dto.niches import NicheTemplate
from app.schemas.typings.niches.strings import IntegrationName
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey as Choice,
)
from app.schemas.typings.profiles.constrained_strings import QuestionKey

NICHE: NicheKey = NicheKey.REAL_ESTATE


def build_real_estate_template() -> NicheTemplate:
    """Real estate and developers: lead qualification and viewings (wave B)."""

    return NicheTemplate(
        key=NICHE,
        wave=LaunchWave.B,
        names=text(NICHE, "name"),
        descriptions=text(NICHE, "description"),
        recommended_plans=[PlanKey.PLUS],
        resource_kind=ResourceKind.STAFF,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(NICHE, "resource_noun"),
        knowledge_kinds=[
            KnowledgeItemKind.PRODUCT,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                NICHE,
                QuestionKey("property_types"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                is_required=True,
                choices=(
                    Choice("apartments"),
                    Choice("houses"),
                    Choice("commercial"),
                    Choice("land"),
                ),
            ),
            question(NICHE, QuestionKey("projects"), Step.OFFER, Answer.LONG_TEXT),
            question(
                NICHE, QuestionKey("installment_plans"), Step.OFFER, Answer.LONG_TEXT
            ),
            question(
                NICHE, QuestionKey("completion_dates"), Step.OFFER, Answer.LONG_TEXT
            ),
            question(
                NICHE,
                QuestionKey("foreign_buyers"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
            ),
            question(
                NICHE,
                QuestionKey("lead_fields"),
                Step.FAQ_AND_HANDOFF,
                Answer.MULTIPLE_CHOICE,
                choices=(
                    Choice("budget"),
                    Choice("district"),
                    Choice("timeline"),
                    Choice("installment"),
                    Choice("purpose"),
                ),
            ),
        ],
        prompt_rules=prompt_rules(
            "Qualify every buyer before passing the lead: ask for the details "
            "listed in the profile (budget, district, timeline, installments).",
            "Quote prices only as 'from' prices from the price list; a manager "
            "confirms which units are still available.",
            "Do not give legal, tax or investment advice and never promise returns "
            "or price growth.",
        ),
        example_exchanges=REAL_ESTATE_EXAMPLES,
        default_handoff_rules=handoff_rules(NICHE),
        default_forbidden_rules=forbidden_rules(NICHE),
        autotest_kinds=autotest_kinds(),
        integrations=[IntegrationName("CRM"), IntegrationName("Google Sheets")],
    )
