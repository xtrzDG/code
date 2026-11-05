from app.registries.niches.examples.trade_examples import ONLINE_SHOP_EXAMPLES
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

NICHE: NicheKey = NicheKey.ONLINE_SHOP


def build_online_shop_template() -> NicheTemplate:
    """
    Instagram and online shops (wave C).

    Shops take no bookings: orders become leads for a manager.
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
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                NICHE,
                QuestionKey("product_categories"),
                Step.NICHE_AND_LANGUAGES,
                Answer.SHORT_TEXT,
                is_required=True,
            ),
            question(
                NICHE,
                QuestionKey("delivery_options"),
                Step.OFFER,
                Answer.LONG_TEXT,
                is_required=True,
            ),
            question(
                NICHE,
                QuestionKey("payment_methods"),
                Step.OFFER,
                Answer.MULTIPLE_CHOICE,
                choices=(
                    Choice("cash_on_delivery"),
                    Choice("card"),
                    Choice("bank_transfer"),
                    Choice("payment_link"),
                ),
            ),
            question(
                NICHE,
                QuestionKey("returns_policy"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
            ),
            question(
                NICHE, QuestionKey("size_guide"), Step.FAQ_AND_HANDOFF, Answer.LONG_TEXT
            ),
            question(
                NICHE,
                QuestionKey("order_status_info"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
            ),
            question(
                NICHE,
                QuestionKey("lead_fields"),
                Step.FAQ_AND_HANDOFF,
                Answer.MULTIPLE_CHOICE,
                choices=(
                    Choice("product"),
                    Choice("size_or_variant"),
                    Choice("delivery_address"),
                    Choice("payment_method"),
                ),
            ),
        ],
        prompt_rules=prompt_rules(
            "You do not take payments or confirm orders: collect the product, "
            "size, quantity and delivery address and create an order lead for a "
            "manager.",
            "State stock and sizes only from the knowledge base; if unsure, say a "
            "manager will confirm.",
            "Do not invent delivery times or delivery prices.",
        ),
        example_exchanges=ONLINE_SHOP_EXAMPLES,
        default_handoff_rules=handoff_rules(NICHE),
        default_forbidden_rules=forbidden_rules(NICHE),
        autotest_kinds=autotest_kinds(),
        integrations=[IntegrationName("Google Sheets")],
    )
