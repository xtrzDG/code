from app.registries.niches.examples.care_examples import CLINIC_EXAMPLES
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
from app.schemas.typings.niches.strings import IntegrationName
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey as Choice,
)
from app.schemas.typings.profiles.constrained_strings import QuestionKey

NICHE: NicheKey = NicheKey.CLINIC


def build_clinic_template() -> NicheTemplate:
    """
    Dental and private clinics (wave B).

    Health data needs a lawyer's review before launch, and the assistant never
    gives medical advice: it books visits and sends emergencies to people.
    """

    return NicheTemplate(
        key=NICHE,
        wave=LaunchWave.B,
        names=text(NICHE, "name"),
        descriptions=text(NICHE, "description"),
        recommended_plans=[PlanKey.VOICE_AND_CHAT],
        resource_kind=ResourceKind.STAFF,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(NICHE, "resource_noun"),
        knowledge_kinds=[
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                NICHE,
                QuestionKey("specialties"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                is_required=True,
                choices=(
                    Choice("dentistry"),
                    Choice("general_practice"),
                    Choice("pediatrics"),
                    Choice("gynecology"),
                    Choice("dermatology"),
                    Choice("ophthalmology"),
                    Choice("diagnostics"),
                    Choice("other"),
                ),
            ),
            question(NICHE, QuestionKey("doctors"), Step.OFFER, Answer.LONG_TEXT),
            question(
                NICHE, QuestionKey("children_accepted"), Step.OFFER, Answer.YES_NO
            ),
            question(
                NICHE, QuestionKey("insurance"), Step.FAQ_AND_HANDOFF, Answer.SHORT_TEXT
            ),
            question(
                NICHE,
                QuestionKey("visit_preparation"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
            ),
            question(
                NICHE,
                QuestionKey("emergency_message"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
                is_required=True,
            ),
        ],
        prompt_rules=prompt_rules(
            "Never give medical advice, diagnoses, interpretations of symptoms or "
            "test results, or medication recommendations; you only book visits "
            "and share facts from the profile.",
            "If the patient describes urgent symptoms or an emergency, tell them "
            "to call the local emergency number immediately and hand off with "
            "critical urgency.",
            "Ask only for what a booking needs (name, phone, doctor or service); "
            "do not ask about health details.",
            "Share preparation instructions only as written in the profile.",
        ),
        example_exchanges=CLINIC_EXAMPLES,
        default_handoff_rules=handoff_rules(NICHE),
        default_forbidden_rules=forbidden_rules(NICHE),
        autotest_kinds=autotest_kinds(AutotestScenarioKind.EMERGENCY),
        booking_variants=[BookingScenarioVariant.SPECIFIC_PERFORMER],
        integrations=[IntegrationName("Google Calendar")],
        requires_legal_review=True,
    )
