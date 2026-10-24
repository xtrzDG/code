from app.registries.niches.examples.service_examples import EDUCATION_EXAMPLES
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

NICHE: NicheKey = NicheKey.EDUCATION


def build_education_template() -> NicheTemplate:
    """Schools, courses, clubs and driving schools: trial lessons (wave C)."""

    return NicheTemplate(
        key=NICHE,
        wave=LaunchWave.C,
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
                QuestionKey("subjects"),
                Step.NICHE_AND_LANGUAGES,
                Answer.SHORT_TEXT,
                is_required=True,
            ),
            question(
                NICHE,
                QuestionKey("age_groups"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                choices=(Choice("kids"), Choice("teens"), Choice("adults")),
            ),
            question(
                NICHE,
                QuestionKey("trial_lesson"),
                Step.OFFER,
                Answer.SINGLE_CHOICE,
                choices=(Choice("free"), Choice("paid"), Choice("none")),
            ),
            question(
                NICHE,
                QuestionKey("lesson_formats"),
                Step.OFFER,
                Answer.MULTIPLE_CHOICE,
                choices=(Choice("group"), Choice("individual"), Choice("online")),
            ),
            question(
                NICHE, QuestionKey("group_schedule"), Step.OFFER, Answer.LONG_TEXT
            ),
            question(
                NICHE,
                QuestionKey("payment_terms"),
                Step.BOOKING_RULES,
                Answer.LONG_TEXT,
            ),
            question(
                NICHE,
                QuestionKey("lead_fields"),
                Step.FAQ_AND_HANDOFF,
                Answer.MULTIPLE_CHOICE,
                choices=(
                    Choice("student_age"),
                    Choice("level"),
                    Choice("preferred_time"),
                    Choice("format"),
                ),
            ),
        ],
        prompt_rules=prompt_rules(
            "Sign students up for trial lessons only into free slots from "
            "check_availability.",
            "Quote course prices and payment terms only from the profile and the "
            "price list.",
            "Do not promise exam results or certificates that are not in the profile.",
        ),
        example_exchanges=EDUCATION_EXAMPLES,
        default_handoff_rules=handoff_rules(NICHE),
        default_forbidden_rules=forbidden_rules(NICHE),
        autotest_kinds=autotest_kinds(),
    )
