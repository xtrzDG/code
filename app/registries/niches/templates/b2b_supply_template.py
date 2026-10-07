from app.registries.niches.examples.trade_examples import B2B_SUPPLY_EXAMPLES
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

NICHE: NicheKey = NicheKey.B2B_SUPPLY


def build_b2b_supply_template() -> NicheTemplate:
    """
    B2B: building materials and furniture (wave C).

    Suppliers take no bookings: requests with volumes become leads.
    """

    return NicheTemplate(
        key=NICHE,
        wave=LaunchWave.C,
        names=text(NICHE, "name"),
        descriptions=text(NICHE, "description"),
        recommended_plans=[PlanKey.CHAT],
        resource_kind=ResourceKind.SLOT,
        booking_unit=BookingUnit.TIME_SLOT,
        takes_bookings=False,
        resource_nouns=text(NICHE, "resource_noun"),
        knowledge_kinds=[
            KnowledgeItemKind.PRODUCT,
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                NICHE,
                QuestionKey("product_categories"),
                Step.NICHE_AND_LANGUAGES,
                Answer.LONG_TEXT,
                is_required=True,
            ),
            question(
                NICHE, QuestionKey("minimum_order"), Step.OFFER, Answer.SHORT_TEXT
            ),
            question(
                NICHE, QuestionKey("delivery_terms"), Step.OFFER, Answer.LONG_TEXT
            ),
            question(
                NICHE, QuestionKey("wholesale_pricing"), Step.OFFER, Answer.LONG_TEXT
            ),
            question(NICHE, QuestionKey("custom_orders"), Step.OFFER, Answer.YES_NO),
            question(
                NICHE,
                QuestionKey("lead_fields"),
                Step.FAQ_AND_HANDOFF,
                Answer.MULTIPLE_CHOICE,
                choices=(
                    Choice("company_name"),
                    Choice("products_and_volumes"),
                    Choice("delivery_address"),
                    Choice("deadline"),
                ),
            ),
        ],
        prompt_rules=prompt_rules(
            "Quote only 'from' prices from the price list; exact offers, volume "
            "discounts and delivery costs come from a manager.",
            "Collect the company, products, volumes, delivery address and deadline "
            "and create an order lead.",
        ),
        example_exchanges=B2B_SUPPLY_EXAMPLES,
        default_handoff_rules=handoff_rules(NICHE),
        default_forbidden_rules=forbidden_rules(NICHE),
        autotest_kinds=autotest_kinds(),
    )
