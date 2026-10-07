from app.registries.niches.examples.service_examples import ENTERTAINMENT_EXAMPLES
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

NICHE: NicheKey = NicheKey.ENTERTAINMENT


def build_entertainment_template() -> NicheTemplate:
    """VR, escape rooms, game and kids' centers: sessions and parties (wave A)."""

    return NicheTemplate(
        key=NICHE,
        wave=LaunchWave.A,
        names=text(NICHE, "name"),
        descriptions=text(NICHE, "description"),
        recommended_plans=[PlanKey.CHAT, PlanKey.VOICE_AND_CHAT],
        resource_kind=ResourceKind.ARENA,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(NICHE, "resource_noun"),
        knowledge_kinds=[
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.PACKAGE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                NICHE,
                QuestionKey("venue_type"),
                Step.NICHE_AND_LANGUAGES,
                Answer.SINGLE_CHOICE,
                is_required=True,
                choices=(
                    Choice("vr_club"),
                    Choice("escape_room"),
                    Choice("game_center"),
                    Choice("kids_center"),
                    Choice("other"),
                ),
            ),
            question(
                NICHE,
                QuestionKey("min_age"),
                Step.FAQ_AND_HANDOFF,
                Answer.NUMBER,
                is_required=True,
            ),
            question(
                NICHE,
                QuestionKey("visitor_rules"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
            ),
            question(
                NICHE,
                QuestionKey("max_players_per_session"),
                Step.BOOKING_RULES,
                Answer.NUMBER,
            ),
            question(
                NICHE,
                QuestionKey("prepayment"),
                Step.BOOKING_RULES,
                Answer.SINGLE_CHOICE,
                choices=(
                    Choice("never"),
                    Choice("groups_and_events"),
                    Choice("always"),
                ),
            ),
            question(
                NICHE, QuestionKey("birthday_packages"), Step.OFFER, Answer.YES_NO
            ),
            question(NICHE, QuestionKey("corporate_events"), Step.OFFER, Answer.YES_NO),
        ],
        prompt_rules=prompt_rules(
            "Check free slots with check_availability before you suggest a time "
            "and book the exact arena or room for the whole session.",
            "State age limits and visitor rules only as written in the profile.",
            "For birthdays, corporate events and large groups, offer the packages "
            "from the price list, mention the prepayment rule and create a lead "
            "with the date, number of guests and wishes.",
        ),
        example_exchanges=ENTERTAINMENT_EXAMPLES,
        default_handoff_rules=handoff_rules(NICHE),
        default_forbidden_rules=forbidden_rules(NICHE),
        autotest_kinds=autotest_kinds(),
        integrations=[
            IntegrationName("Google Calendar"),
            IntegrationName("Cal.com"),
        ],
    )
