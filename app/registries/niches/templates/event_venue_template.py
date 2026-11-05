from app.registries.niches.examples.hospitality_examples import EVENT_VENUE_EXAMPLES
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

NICHE: NicheKey = NicheKey.EVENT_VENUE


def build_event_venue_template() -> NicheTemplate:
    """Banquet halls, wedding venues and catering: requests to managers (wave B)."""

    return NicheTemplate(
        key=NICHE,
        wave=LaunchWave.B,
        names=text(NICHE, "name"),
        descriptions=text(NICHE, "description"),
        recommended_plans=[PlanKey.CHAT, PlanKey.VOICE_AND_CHAT],
        resource_kind=ResourceKind.ROOM,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(NICHE, "resource_noun"),
        knowledge_kinds=[
            KnowledgeItemKind.PACKAGE,
            KnowledgeItemKind.MENU_ITEM,
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                NICHE,
                QuestionKey("event_types"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                is_required=True,
                choices=(
                    Choice("wedding"),
                    Choice("birthday"),
                    Choice("corporate"),
                    Choice("conference"),
                    Choice("catering_only"),
                ),
            ),
            question(
                NICHE,
                QuestionKey("max_guests"),
                Step.BOOKING_RULES,
                Answer.NUMBER,
                is_required=True,
            ),
            question(
                NICHE,
                QuestionKey("catering"),
                Step.OFFER,
                Answer.SINGLE_CHOICE,
                choices=(
                    Choice("own_kitchen"),
                    Choice("external_allowed"),
                    Choice("no_food"),
                ),
            ),
            question(NICHE, QuestionKey("own_drinks"), Step.OFFER, Answer.YES_NO),
            question(
                NICHE, QuestionKey("decor_and_equipment"), Step.OFFER, Answer.LONG_TEXT
            ),
            question(
                NICHE,
                QuestionKey("lead_fields"),
                Step.FAQ_AND_HANDOFF,
                Answer.MULTIPLE_CHOICE,
                choices=(
                    Choice("event_date"),
                    Choice("guest_count"),
                    Choice("budget"),
                    Choice("menu_wishes"),
                    Choice("contact_time"),
                ),
            ),
        ],
        prompt_rules=prompt_rules(
            "Every event request becomes a lead: collect the date, number of "
            "guests, budget and menu wishes and pass them to a manager.",
            "Name free dates only from check_availability; a manager confirms the "
            "event date.",
            "Quote packages and per-person prices only from the price list.",
        ),
        example_exchanges=EVENT_VENUE_EXAMPLES,
        default_handoff_rules=handoff_rules(NICHE),
        default_forbidden_rules=forbidden_rules(NICHE),
        autotest_kinds=autotest_kinds(),
    )
