from app.registries.niches.examples.care_examples import BEAUTY_SALON_EXAMPLES
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
from app.schemas.constants.niches import BookingScenarioVariant, LaunchWave, NicheKey
from app.schemas.constants.niches import ProfileWizardStep as Step
from app.schemas.constants.niches import QuestionAnswerType as Answer
from app.schemas.dto.niches import NicheTemplate
from app.schemas.typings.niches.strings import IntegrationName
from app.schemas.typings.profiles.constrained_strings import (
    FactKey,
    QuestionKey,
)
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey as Choice,
)

NICHE: NicheKey = NicheKey.BEAUTY_SALON


def build_beauty_salon_template() -> NicheTemplate:
    """Beauty salons, barbershops and spas: appointments with masters (wave A)."""

    return NicheTemplate(
        key=NICHE,
        wave=LaunchWave.A,
        names=text(NICHE, "name"),
        descriptions=text(NICHE, "description"),
        recommended_plans=[PlanKey.CHAT],
        resource_kind=ResourceKind.STAFF,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(NICHE, "resource_noun"),
        knowledge_kinds=[
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.PACKAGE,
            KnowledgeItemKind.PRODUCT,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                NICHE,
                QuestionKey("service_categories"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                is_required=True,
                choices=(
                    Choice("hair"),
                    Choice("nails"),
                    Choice("makeup"),
                    Choice("brows_lashes"),
                    Choice("cosmetology"),
                    Choice("massage"),
                    Choice("barber"),
                    Choice("spa"),
                ),
            ),
            question(
                NICHE, QuestionKey("masters_and_services"), Step.OFFER, Answer.LONG_TEXT
            ),
            question(
                NICHE, QuestionKey("product_brands"), Step.OFFER, Answer.SHORT_TEXT
            ),
            question(
                NICHE,
                QuestionKey("break_between_appointments"),
                Step.BOOKING_RULES,
                Answer.NUMBER,
                fact_key=FactKey("appointment_break_minutes"),
            ),
            question(
                NICHE,
                QuestionKey("client_chooses_master"),
                Step.BOOKING_RULES,
                Answer.YES_NO,
            ),
            question(
                NICHE,
                QuestionKey("late_arrival_policy"),
                Step.BOOKING_RULES,
                Answer.LONG_TEXT,
            ),
        ],
        prompt_rules=prompt_rules(
            "Every service has a duration in the price list: book a slot long "
            "enough for the service with a master who does it.",
            "If the client names a master, book only with that master; otherwise "
            "offer the earliest free master.",
            "Do not judge skin, hair or health conditions; suggest a consultation "
            "with a master instead.",
        ),
        example_exchanges=BEAUTY_SALON_EXAMPLES,
        default_handoff_rules=handoff_rules(NICHE),
        default_forbidden_rules=forbidden_rules(NICHE),
        autotest_kinds=autotest_kinds(),
        booking_variants=[BookingScenarioVariant.SPECIFIC_PERFORMER],
        integrations=[
            IntegrationName("Google Calendar"),
            IntegrationName("Cal.com"),
        ],
    )
