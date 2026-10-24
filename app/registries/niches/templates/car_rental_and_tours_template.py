from app.registries.niches.examples.trade_examples import CAR_RENTAL_AND_TOURS_EXAMPLES
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
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey as Choice,
)
from app.schemas.typings.profiles.constrained_strings import QuestionKey

NICHE: NicheKey = NicheKey.CAR_RENTAL_AND_TOURS


def build_car_rental_and_tours_template() -> NicheTemplate:
    """Car rental, transfers and tours: fleet, deposit, prepayment (wave B)."""

    return NicheTemplate(
        key=NICHE,
        wave=LaunchWave.B,
        names=text(NICHE, "name"),
        descriptions=text(NICHE, "description"),
        recommended_plans=[PlanKey.CHAT, PlanKey.VOICE_AND_CHAT],
        resource_kind=ResourceKind.VEHICLE,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(NICHE, "resource_noun"),
        knowledge_kinds=[
            KnowledgeItemKind.VEHICLE,
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.PACKAGE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                NICHE,
                QuestionKey("offer_types"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                is_required=True,
                choices=(Choice("car_rental"), Choice("transfers"), Choice("tours")),
            ),
            question(
                NICHE,
                QuestionKey("roadside_phone"),
                Step.CONTACTS_AND_HOURS,
                Answer.PHONE_NUMBER,
            ),
            question(NICHE, QuestionKey("fleet"), Step.OFFER, Answer.LONG_TEXT),
            question(
                NICHE, QuestionKey("pickup_options"), Step.OFFER, Answer.LONG_TEXT
            ),
            question(
                NICHE, QuestionKey("tour_languages"), Step.OFFER, Answer.SHORT_TEXT
            ),
            question(
                NICHE,
                QuestionKey("security_deposit"),
                Step.BOOKING_RULES,
                Answer.SHORT_TEXT,
            ),
            question(
                NICHE,
                QuestionKey("driver_requirements"),
                Step.BOOKING_RULES,
                Answer.LONG_TEXT,
            ),
        ],
        prompt_rules=prompt_rules(
            "Check availability for the exact dates before you confirm a car, a "
            "transfer or a tour.",
            "A booking with prepayment is confirmed only after payment by the "
            "payment link from the profile.",
            "State the deposit and driver requirements only as written in the profile.",
        ),
        example_exchanges=CAR_RENTAL_AND_TOURS_EXAMPLES,
        default_handoff_rules=handoff_rules(NICHE),
        default_forbidden_rules=forbidden_rules(NICHE),
        autotest_kinds=autotest_kinds(),
    )
