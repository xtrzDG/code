from app.registries.niches.examples.hospitality_examples import HOTEL_EXAMPLES
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
    QuestionChoiceKey as Choice,
)
from app.schemas.typings.profiles.constrained_strings import QuestionKey

NICHE: NicheKey = NicheKey.HOTEL


def build_hotel_template() -> NicheTemplate:
    """Hotels, guest houses and hostels: rooms booked by nights (wave A)."""

    return NicheTemplate(
        key=NICHE,
        wave=LaunchWave.A,
        names=text(NICHE, "name"),
        descriptions=text(NICHE, "description"),
        recommended_plans=[PlanKey.VOICE_AND_CHAT, PlanKey.PLUS],
        resource_kind=ResourceKind.ROOM,
        booking_unit=BookingUnit.NIGHT,
        resource_nouns=text(NICHE, "resource_noun"),
        knowledge_kinds=[
            KnowledgeItemKind.ROOM_TYPE,
            KnowledgeItemKind.PACKAGE,
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                NICHE,
                QuestionKey("property_type"),
                Step.NICHE_AND_LANGUAGES,
                Answer.SINGLE_CHOICE,
                is_required=True,
                choices=(
                    Choice("hotel"),
                    Choice("guest_house"),
                    Choice("hostel"),
                    Choice("apart_hotel"),
                ),
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
                QuestionKey("early_check_in"),
                Step.BOOKING_RULES,
                Answer.LONG_TEXT,
            ),
            question(
                NICHE, QuestionKey("seasonal_prices"), Step.OFFER, Answer.LONG_TEXT
            ),
            question(
                NICHE,
                QuestionKey("breakfast"),
                Step.OFFER,
                Answer.SINGLE_CHOICE,
                choices=(Choice("none"), Choice("included"), Choice("extra_charge")),
            ),
            question(
                NICHE,
                QuestionKey("transfer"),
                Step.OFFER,
                Answer.SINGLE_CHOICE,
                choices=(Choice("none"), Choice("paid"), Choice("free")),
            ),
            question(
                NICHE, QuestionKey("pets_allowed"), Step.FAQ_AND_HANDOFF, Answer.YES_NO
            ),
            question(
                NICHE,
                QuestionKey("booking_system"),
                Step.CHANNELS,
                Answer.SINGLE_CHOICE,
                choices=(
                    Choice("none"),
                    Choice("cloudbeds"),
                    Choice("mews"),
                    Choice("hotelrunner"),
                    Choice("other"),
                ),
            ),
        ],
        prompt_rules=prompt_rules(
            "Rooms are booked by nights: always confirm the check-in date, the "
            "number of nights and the number of guests.",
            "Quote room prices only from the price list and only for the season "
            "that matches the dates; if the season is unclear, say the price "
            "depends on the dates and check get_price.",
            "Offer the direct booking link or a booking through you; never "
            "recommend booking through other platforms.",
            "Guests also write at night: answer arrival questions yourself, but "
            "pass emergencies and complaints to staff right away.",
        ),
        example_exchanges=HOTEL_EXAMPLES,
        default_handoff_rules=handoff_rules(NICHE),
        default_forbidden_rules=forbidden_rules(NICHE),
        autotest_kinds=autotest_kinds(),
        booking_variants=[BookingScenarioVariant.ROOM_TYPE_STAY],
        integrations=[
            IntegrationName("Cloudbeds"),
            IntegrationName("Mews"),
            IntegrationName("HotelRunner"),
        ],
    )
