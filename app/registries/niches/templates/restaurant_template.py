from app.registries.niches.examples.hospitality_examples import RESTAURANT_EXAMPLES
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

NICHE: NicheKey = NicheKey.RESTAURANT


def build_restaurant_template() -> NicheTemplate:
    """Restaurants and cafes: tables, menu, banquets, delivery link (wave A)."""

    return NicheTemplate(
        key=NICHE,
        wave=LaunchWave.A,
        names=text(NICHE, "name"),
        descriptions=text(NICHE, "description"),
        recommended_plans=[PlanKey.VOICE_AND_CHAT],
        resource_kind=ResourceKind.TABLE,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(NICHE, "resource_noun"),
        knowledge_kinds=[
            KnowledgeItemKind.MENU_ITEM,
            KnowledgeItemKind.PACKAGE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                NICHE,
                QuestionKey("cuisine"),
                Step.NICHE_AND_LANGUAGES,
                Answer.SHORT_TEXT,
                is_required=True,
            ),
            question(
                NICHE,
                QuestionKey("seating_capacity"),
                Step.BOOKING_RULES,
                Answer.NUMBER,
            ),
            question(
                NICHE,
                QuestionKey("banquets"),
                Step.OFFER,
                Answer.SINGLE_CHOICE,
                choices=(Choice("no"), Choice("separate_hall"), Choice("whole_venue")),
            ),
            question(
                NICHE, QuestionKey("banquet_max_guests"), Step.OFFER, Answer.NUMBER
            ),
            question(
                NICHE,
                QuestionKey("delivery"),
                Step.OFFER,
                Answer.SINGLE_CHOICE,
                choices=(
                    Choice("none"),
                    Choice("own_couriers"),
                    Choice("delivery_apps"),
                ),
            ),
            question(NICHE, QuestionKey("live_music"), Step.OFFER, Answer.SHORT_TEXT),
            question(NICHE, QuestionKey("kids_menu"), Step.OFFER, Answer.YES_NO),
            question(NICHE, QuestionKey("outdoor_seating"), Step.OFFER, Answer.YES_NO),
            question(
                NICHE,
                QuestionKey("dietary_options"),
                Step.OFFER,
                Answer.MULTIPLE_CHOICE,
                choices=(
                    Choice("vegetarian"),
                    Choice("vegan"),
                    Choice("gluten_free"),
                    Choice("halal"),
                    Choice("kosher"),
                ),
            ),
            question(
                NICHE,
                QuestionKey("allergen_policy"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
            ),
        ],
        prompt_rules=prompt_rules(
            "Mention allergens and ingredients only as written in the profile or "
            "the knowledge base; pass any other allergy question to staff.",
            "A table booking needs a date, a time, the number of guests and a name.",
            "For banquets, birthdays and groups larger than the maximum party "
            "size, collect the date, number of guests, budget and wishes and "
            "create a lead instead of a booking.",
            "Do not take delivery orders yourself; send the delivery link when "
            "there is one.",
        ),
        example_exchanges=RESTAURANT_EXAMPLES,
        default_handoff_rules=handoff_rules(NICHE),
        default_forbidden_rules=forbidden_rules(NICHE),
        autotest_kinds=autotest_kinds(),
        integrations=[
            IntegrationName("Google Calendar"),
            IntegrationName("Poster"),
            IntegrationName("Loyverse"),
        ],
    )
