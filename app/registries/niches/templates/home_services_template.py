from app.registries.niches.examples.service_examples import HOME_SERVICES_EXAMPLES
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

NICHE: NicheKey = NicheKey.HOME_SERVICES


def build_home_services_template() -> NicheTemplate:
    """Home services: cleaning, repairs and handymen at the customer (wave C)."""

    return NicheTemplate(
        key=NICHE,
        wave=LaunchWave.C,
        names=text(NICHE, "name"),
        descriptions=text(NICHE, "description"),
        recommended_plans=[PlanKey.CHAT],
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
                QuestionKey("service_types"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                is_required=True,
                choices=(
                    Choice("cleaning"),
                    Choice("plumbing"),
                    Choice("electrical"),
                    Choice("appliance_repair"),
                    Choice("renovation"),
                    Choice("handyman"),
                ),
            ),
            question(
                NICHE,
                QuestionKey("service_area"),
                Step.CONTACTS_AND_HOURS,
                Answer.SHORT_TEXT,
                is_required=True,
            ),
            question(
                NICHE,
                QuestionKey("pricing_basis"),
                Step.OFFER,
                Answer.SINGLE_CHOICE,
                choices=(
                    Choice("per_hour"),
                    Choice("per_square_meter"),
                    Choice("per_job"),
                    Choice("after_inspection"),
                ),
            ),
            question(NICHE, QuestionKey("call_out_fee"), Step.OFFER, Answer.SHORT_TEXT),
            question(
                NICHE, QuestionKey("ask_for_photos"), Step.BOOKING_RULES, Answer.YES_NO
            ),
            question(
                NICHE,
                QuestionKey("lead_fields"),
                Step.FAQ_AND_HANDOFF,
                Answer.MULTIPLE_CHOICE,
                choices=(
                    Choice("address"),
                    Choice("task_description"),
                    Choice("photos"),
                    Choice("preferred_time"),
                ),
            ),
        ],
        prompt_rules=prompt_rules(
            "Give estimates only from the price list and say that the specialist "
            "confirms the final price.",
            "Collect the address, a description of the task and a convenient time "
            "before you book a visit.",
            "For emergencies such as a water leak, a gas smell or sparking wiring, "
            "tell the customer to call the local emergency service first and hand "
            "off with high urgency.",
        ),
        example_exchanges=HOME_SERVICES_EXAMPLES,
        default_handoff_rules=handoff_rules(NICHE),
        default_forbidden_rules=forbidden_rules(NICHE),
        autotest_kinds=autotest_kinds(),
    )
