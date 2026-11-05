from app.registries.niches.examples.care_examples import VETERINARY_EXAMPLES
from app.registries.niches.template_parts import (
    autotest_kinds,
    forbidden_rules,
    handoff_rules,
    prompt_rules,
    question,
    text,
)
from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import BookingScenarioVariant, LaunchWave, NicheKey
from app.schemas.constants.niches import ProfileWizardStep as Step
from app.schemas.constants.niches import QuestionAnswerType as Answer
from app.schemas.dto.niches import NicheTemplate
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey as Choice,
)
from app.schemas.typings.profiles.constrained_strings import QuestionKey

NICHE: NicheKey = NicheKey.VETERINARY


def build_veterinary_template() -> NicheTemplate:
    """
    Veterinary clinics and grooming (wave C).

    The assistant never gives veterinary advice; an animal in danger goes to a
    person at once.
    """

    return NicheTemplate(
        key=NICHE,
        wave=LaunchWave.C,
        names=text(NICHE, "name"),
        descriptions=text(NICHE, "description"),
        recommended_plans=[PlanKey.VOICE_AND_CHAT],
        resource_kind=ResourceKind.STAFF,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(NICHE, "resource_noun"),
        knowledge_kinds=[
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.PRODUCT,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                NICHE,
                QuestionKey("animals_treated"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                is_required=True,
                choices=(
                    Choice("dogs"),
                    Choice("cats"),
                    Choice("birds"),
                    Choice("rodents"),
                    Choice("exotic"),
                ),
            ),
            question(
                NICHE,
                QuestionKey("services_offered"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                choices=(
                    Choice("treatment"),
                    Choice("vaccination"),
                    Choice("surgery"),
                    Choice("grooming"),
                    Choice("pet_hotel"),
                ),
            ),
            question(
                NICHE,
                QuestionKey("emergency_hours"),
                Step.CONTACTS_AND_HOURS,
                Answer.LONG_TEXT,
                is_required=True,
            ),
            question(NICHE, QuestionKey("home_visits"), Step.OFFER, Answer.YES_NO),
            question(
                NICHE,
                QuestionKey("visit_preparation"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
            ),
        ],
        prompt_rules=prompt_rules(
            "Never give veterinary advice, diagnoses or medication doses; you only "
            "book visits and share facts from the profile.",
            "If an animal is in danger (bleeding, poisoning, breathing problems, "
            "injury), tell the owner how to reach emergency care from the profile "
            "and hand off with critical urgency.",
            "Ask for the kind of animal and the service when booking.",
        ),
        example_exchanges=VETERINARY_EXAMPLES,
        default_handoff_rules=handoff_rules(NICHE),
        default_forbidden_rules=forbidden_rules(NICHE),
        autotest_kinds=autotest_kinds(AutotestScenarioKind.EMERGENCY),
        booking_variants=[BookingScenarioVariant.SPECIFIC_PERFORMER],
    )
