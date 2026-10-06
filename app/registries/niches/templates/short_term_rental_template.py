from app.registries.niches.examples.hospitality_examples import (
    SHORT_TERM_RENTAL_EXAMPLES,
)
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
from app.schemas.typings.profiles.constrained_strings import QuestionKey

NICHE: NicheKey = NicheKey.SHORT_TERM_RENTAL


def build_short_term_rental_template() -> NicheTemplate:
    """Short-term rental apartments: stays booked by nights (wave B)."""

    return NicheTemplate(
        key=NICHE,
        wave=LaunchWave.B,
        names=text(NICHE, "name"),
        descriptions=text(NICHE, "description"),
        recommended_plans=[PlanKey.CHAT],
        resource_kind=ResourceKind.ROOM,
        booking_unit=BookingUnit.NIGHT,
        resource_nouns=text(NICHE, "resource_noun"),
        knowledge_kinds=[
            KnowledgeItemKind.ROOM_TYPE,
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                NICHE,
                QuestionKey("apartment_count"),
                Step.NICHE_AND_LANGUAGES,
                Answer.NUMBER,
                is_required=True,
            ),
            question(
                NICHE,
                QuestionKey("host_phone"),
                Step.CONTACTS_AND_HOURS,
                Answer.PHONE_NUMBER,
            ),
            question(
                NICHE,
                QuestionKey("check_in_time"),
                Step.BOOKING_RULES,
                Answer.SHORT_TEXT,
                is_required=True,
            ),
            question(
                NICHE,
                QuestionKey("check_out_time"),
                Step.BOOKING_RULES,
                Answer.SHORT_TEXT,
                is_required=True,
            ),
            question(
                NICHE,
                QuestionKey("extension_policy"),
                Step.BOOKING_RULES,
                Answer.LONG_TEXT,
            ),
            question(
                NICHE,
                QuestionKey("check_in_instructions"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
            ),
            question(
                NICHE, QuestionKey("wifi_info"), Step.FAQ_AND_HANDOFF, Answer.LONG_TEXT
            ),
            question(
                NICHE,
                QuestionKey("house_rules"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
            ),
        ],
        prompt_rules=prompt_rules(
            "Apartments are booked by nights: confirm the check-in date, the "
            "number of nights and the number of guests before booking.",
            "Share check-in instructions, Wi-Fi details and house rules only as "
            "written in the profile.",
            "Never share door, lock-box or safe codes.",
            "If a guest cannot get in or something is broken, hand off to the host "
            "with high urgency.",
        ),
        example_exchanges=SHORT_TERM_RENTAL_EXAMPLES,
        default_handoff_rules=handoff_rules(NICHE),
        default_forbidden_rules=forbidden_rules(NICHE),
        autotest_kinds=autotest_kinds(),
        booking_variants=[BookingScenarioVariant.ROOM_TYPE_STAY],
        integrations=[IntegrationName("WhatsApp")],
    )
