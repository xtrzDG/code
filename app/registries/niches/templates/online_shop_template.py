from app.registries.niches.template_parts import (
    autotest_kinds,
    choice,
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


def build_online_shop_template() -> NicheTemplate:
    """
    Instagram and online shops (wave C).

    Shops take no bookings: orders become leads for a manager.
    """

    return NicheTemplate(
        key=NicheKey.ONLINE_SHOP,
        wave=LaunchWave.C,
        names=text(
            en="Instagram and online shops",
            ru="Магазины в Instagram и интернет-магазины",
            ka="Instagram-მაღაზიები და ინტერნეტ-მაღაზიები",
        ),
        descriptions=text(
            en="Stock, sizes, delivery, order status and orders passed to a manager.",
            ru="Наличие, размеры, доставка, статус заказа, оформление заказа с "
            "передачей менеджеру.",
            ka="მარაგი, ზომები, მიტანა, შეკვეთის სტატუსი და შეკვეთის გადაცემა "
            "მენეჯერისთვის.",
        ),
        recommended_plans=[PlanKey.CHAT],
        resource_kind=ResourceKind.SLOT,
        booking_unit=BookingUnit.TIME_SLOT,
        takes_bookings=False,
        resource_nouns=text(en="order", ru="заказ", ka="შეკვეთა"),
        knowledge_kinds=[
            KnowledgeItemKind.PRODUCT,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                QuestionKey("product_categories"),
                Step.NICHE_AND_LANGUAGES,
                Answer.SHORT_TEXT,
                text(
                    en="What do you sell?",
                    ru="Что вы продаёте?",
                    ka="რას ყიდით?",
                ),
                is_required=True,
            ),
            question(
                QuestionKey("delivery_options"),
                Step.OFFER,
                Answer.LONG_TEXT,
                text(
                    en="Delivery options, times and prices",
                    ru="Варианты доставки, сроки и цены",
                    ka="მიტანის ვარიანტები, ვადები და ფასები",
                ),
                is_required=True,
            ),
            question(
                QuestionKey("payment_methods"),
                Step.OFFER,
                Answer.MULTIPLE_CHOICE,
                text(
                    en="Payment methods",
                    ru="Способы оплаты",
                    ka="გადახდის მეთოდები",
                ),
                choices=[
                    choice(
                        Choice("cash_on_delivery"),
                        "Cash on delivery",
                        "Наличными при получении",
                        "ნაღდით მიღებისას",
                    ),
                    choice(Choice("card"), "Card", "Картой", "ბარათით"),
                    choice(
                        Choice("bank_transfer"),
                        "Bank transfer",
                        "Банковский перевод",
                        "საბანკო გადარიცხვა",
                    ),
                    choice(
                        Choice("payment_link"),
                        "Payment link",
                        "Ссылка на оплату",
                        "გადახდის ბმული",
                    ),
                ],
            ),
            question(
                QuestionKey("returns_policy"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
                text(
                    en="Returns and exchanges",
                    ru="Возврат и обмен",
                    ka="დაბრუნება და გაცვლა",
                ),
            ),
            question(
                QuestionKey("size_guide"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
                text(en="Size guide", ru="Таблица размеров", ka="ზომების ცხრილი"),
            ),
            question(
                QuestionKey("order_status_info"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
                text(
                    en="How do customers learn the status of their order?",
                    ru="Как клиент узнаёт статус заказа?",
                    ka="როგორ იგებს კლიენტი შეკვეთის სტატუსს?",
                ),
            ),
            question(
                QuestionKey("lead_fields"),
                Step.FAQ_AND_HANDOFF,
                Answer.MULTIPLE_CHOICE,
                text(
                    en="What should the assistant collect for an order?",
                    ru="Что помощник собирает для заказа?",
                    ka="რა შეაგროვოს ასისტენტმა შეკვეთისთვის?",
                ),
                choices=[
                    choice(
                        Choice("product"),
                        "Product and quantity",
                        "Товар и количество",
                        "პროდუქტი და რაოდენობა",
                    ),
                    choice(
                        Choice("size_or_variant"),
                        "Size or variant",
                        "Размер или вариант",
                        "ზომა ან ვარიანტი",
                    ),
                    choice(
                        Choice("delivery_address"),
                        "Delivery address",
                        "Адрес доставки",
                        "მიტანის მისამართი",
                    ),
                    choice(
                        Choice("payment_method"),
                        "Payment method",
                        "Способ оплаты",
                        "გადახდის მეთოდი",
                    ),
                ],
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
        default_handoff_rules=handoff_rules(
            en=[
                "Question about the status of an order",
                "Return, exchange or refund",
                "Defective product",
                "Wholesale order",
            ],
            ru=[
                "Вопрос о статусе заказа",
                "Возврат, обмен или возврат денег",
                "Брак",
                "Оптовый заказ",
            ],
            ka=[
                "კითხვა შეკვეთის სტატუსზე",
                "დაბრუნება, გაცვლა ან თანხის დაბრუნება",
                "დეფექტური პროდუქტი",
                "საბითუმო შეკვეთა",
            ],
        ),
        default_forbidden_rules=forbidden_rules(
            en=["Confirming stock or delivery dates that are not in the profile"],
            ru=["Подтверждение наличия или сроков доставки, которых нет в анкете"],
            ka=["მარაგის ან მიტანის ვადების დადასტურება, რომლებიც ანკეტაში არ არის"],
        ),
        autotest_kinds=autotest_kinds(),
        integrations=[IntegrationName("Google Sheets")],
    )
