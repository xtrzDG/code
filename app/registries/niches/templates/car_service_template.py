from app.registries.niches.examples.service_examples import CAR_SERVICE_EXAMPLES
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

NICHE: NicheKey = NicheKey.CAR_SERVICE


def build_car_service_template() -> NicheTemplate:
    """Car services, tire shops and car washes: bays and services (wave B)."""

    return NicheTemplate(
        key=NICHE,
        wave=LaunchWave.B,
        names=text(NICHE, "name"),
        descriptions=text(NICHE, "description"),
        recommended_plans=[PlanKey.VOICE_AND_CHAT],
        resource_kind=ResourceKind.BAY,
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
                QuestionKey("services_offered"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                is_required=True,
                choices=(
                    Choice("diagnostics"),
                    Choice("repair"),
                    Choice("oil_change"),
                    Choice("tire_service"),
                    Choice("car_wash"),
                    Choice("body_work"),
                    Choice("detailing"),
                ),
            ),
            question(NICHE, QuestionKey("car_brands"), Step.OFFER, Answer.SHORT_TEXT),
            question(NICHE, QuestionKey("price_note"), Step.OFFER, Answer.SHORT_TEXT),
            question(
                NICHE,
                QuestionKey("what_to_bring"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
            ),
            question(
                NICHE, QuestionKey("waiting_area"), Step.FAQ_AND_HANDOFF, Answer.YES_NO
            ),
            question(
                NICHE, QuestionKey("warranty"), Step.FAQ_AND_HANDOFF, Answer.SHORT_TEXT
            ),
        ],
        prompt_rules=prompt_rules(
            "Repair prices are 'from' prices: quote them only from the price list "
            "and say that the final price is set after diagnostics.",
            "Book the service bay for the duration of the service from the price list.",
            "Do not diagnose a car over chat or phone; offer a diagnostics "
            "appointment.",
        ),
        example_exchanges=CAR_SERVICE_EXAMPLES,
        default_handoff_rules=handoff_rules(NICHE),
        default_forbidden_rules=forbidden_rules(NICHE),
        autotest_kinds=autotest_kinds(),
        integrations=[IntegrationName("Google Calendar")],
    )
