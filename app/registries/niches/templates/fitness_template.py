from app.registries.niches.examples.care_examples import FITNESS_EXAMPLES
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

NICHE: NicheKey = NicheKey.FITNESS


def build_fitness_template() -> NicheTemplate:
    """Fitness, martial arts and padel: trials, classes, courts (wave B)."""

    return NicheTemplate(
        key=NICHE,
        wave=LaunchWave.B,
        names=text(NICHE, "name"),
        descriptions=text(NICHE, "description"),
        recommended_plans=[PlanKey.CHAT],
        resource_kind=ResourceKind.SLOT,
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
                QuestionKey("activities"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                is_required=True,
                choices=(
                    Choice("gym"),
                    Choice("group_classes"),
                    Choice("martial_arts"),
                    Choice("padel"),
                    Choice("tennis"),
                    Choice("yoga"),
                    Choice("swimming"),
                ),
            ),
            question(
                NICHE,
                QuestionKey("trial_session"),
                Step.OFFER,
                Answer.SINGLE_CHOICE,
                choices=(Choice("free"), Choice("paid"), Choice("none")),
            ),
            question(
                NICHE, QuestionKey("class_schedule"), Step.OFFER, Answer.LONG_TEXT
            ),
            question(NICHE, QuestionKey("court_rental"), Step.OFFER, Answer.YES_NO),
            question(
                NICHE,
                QuestionKey("membership_freeze"),
                Step.BOOKING_RULES,
                Answer.LONG_TEXT,
            ),
            question(
                NICHE,
                QuestionKey("what_to_bring"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
            ),
        ],
        prompt_rules=prompt_rules(
            "Book trial sessions and classes only into free slots from "
            "check_availability.",
            "Quote membership prices and freeze rules only from the profile and "
            "the price list.",
            "Do not give training, nutrition or health advice; suggest talking to "
            "a coach.",
        ),
        example_exchanges=FITNESS_EXAMPLES,
        default_handoff_rules=handoff_rules(NICHE),
        default_forbidden_rules=forbidden_rules(NICHE),
        autotest_kinds=autotest_kinds(),
        integrations=[IntegrationName("Google Calendar")],
    )
