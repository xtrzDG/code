from app.registries.niches.examples.trade_examples import B2B_SUPPLY_EXAMPLES
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
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey as Choice,
)
from app.schemas.typings.profiles.constrained_strings import QuestionKey


def build_b2b_supply_template() -> NicheTemplate:
    """
    B2B: building materials and furniture (wave C).

    Suppliers take no bookings: requests with volumes become leads.
    """

    return NicheTemplate(
        key=NicheKey.B2B_SUPPLY,
        wave=LaunchWave.C,
        names=text(
            en="B2B: building materials and furniture",
            ru="B2B: стройматериалы и мебель",
            ka="B2B: სამშენებლო მასალები და ავეჯი",
        ),
        descriptions=text(
            en="Catalog, 'from' prices, delivery estimates and requests with "
            "volumes passed to a manager.",
            ru="Каталог, цены «от», расчёт доставки, заявки с объёмами — менеджеру.",
            ka="კატალოგი, ფასები „დან“, მიტანის გაანგარიშება და მოთხოვნები "
            "მოცულობებით — მენეჯერს.",
        ),
        recommended_plans=[PlanKey.CHAT],
        resource_kind=ResourceKind.SLOT,
        booking_unit=BookingUnit.TIME_SLOT,
        takes_bookings=False,
        resource_nouns=text(en="order", ru="заказ", ka="შეკვეთა"),
        knowledge_kinds=[
            KnowledgeItemKind.PRODUCT,
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                QuestionKey("product_categories"),
                Step.NICHE_AND_LANGUAGES,
                Answer.LONG_TEXT,
                text(
                    en="Product categories",
                    ru="Категории товаров",
                    ka="პროდუქციის კატეგორიები",
                ),
                is_required=True,
            ),
            question(
                QuestionKey("minimum_order"),
                Step.OFFER,
                Answer.SHORT_TEXT,
                text(
                    en="Minimum order",
                    ru="Минимальный заказ",
                    ka="მინიმალური შეკვეთა",
                ),
            ),
            question(
                QuestionKey("delivery_terms"),
                Step.OFFER,
                Answer.LONG_TEXT,
                text(
                    en="Delivery terms and how delivery is priced",
                    ru="Условия и расчёт доставки",
                    ka="მიტანის პირობები და გაანგარიშება",
                ),
            ),
            question(
                QuestionKey("wholesale_pricing"),
                Step.OFFER,
                Answer.LONG_TEXT,
                text(
                    en="Wholesale and volume prices",
                    ru="Оптовые цены и скидки за объём",
                    ka="საბითუმო ფასები და ფასდაკლება მოცულობაზე",
                ),
                hints=text(
                    en="The assistant quotes 'from' prices; exact offers come "
                    "from a manager.",
                    ru="Помощник называет цены «от»; точное предложение делает "
                    "менеджер.",
                    ka="ასისტენტი ასახელებს ფასებს „დან“; ზუსტ შეთავაზებას "
                    "მენეჯერი ამზადებს.",
                ),
            ),
            question(
                QuestionKey("custom_orders"),
                Step.OFFER,
                Answer.YES_NO,
                text(
                    en="Do you make products to order?",
                    ru="Делаете ли вы изделия на заказ?",
                    ka="ამზადებთ ნაწარმს შეკვეთით?",
                ),
            ),
            question(
                QuestionKey("lead_fields"),
                Step.FAQ_AND_HANDOFF,
                Answer.MULTIPLE_CHOICE,
                text(
                    en="What should the assistant collect for a manager?",
                    ru="Что помощник собирает для менеджера?",
                    ka="რა შეაგროვოს ასისტენტმა მენეჯერისთვის?",
                ),
                choices=[
                    choice(
                        Choice("company_name"),
                        "Company name",
                        "Название компании",
                        "კომპანიის სახელი",
                    ),
                    choice(
                        Choice("products_and_volumes"),
                        "Products and volumes",
                        "Товары и объёмы",
                        "პროდუქცია და მოცულობები",
                    ),
                    choice(
                        Choice("delivery_address"),
                        "Delivery address",
                        "Адрес доставки",
                        "მიტანის მისამართი",
                    ),
                    choice(Choice("deadline"), "Deadline", "Срок", "ვადა"),
                ],
            ),
        ],
        prompt_rules=prompt_rules(
            "Quote only 'from' prices from the price list; exact offers, volume "
            "discounts and delivery costs come from a manager.",
            "Collect the company, products, volumes, delivery address and deadline "
            "and create an order lead.",
        ),
        example_exchanges=B2B_SUPPLY_EXAMPLES,
        default_handoff_rules=handoff_rules(
            en=[
                "Large order or a request for a commercial offer",
                "Custom prices or terms",
                "Delivery outside the usual area",
                "Complaint",
            ],
            ru=[
                "Крупный заказ или запрос коммерческого предложения",
                "Особые цены или условия",
                "Доставка за пределы обычной зоны",
                "Жалоба",
            ],
            ka=[
                "დიდი შეკვეთა ან კომერციული შეთავაზების მოთხოვნა",
                "განსაკუთრებული ფასები ან პირობები",
                "მიტანა ჩვეულებრივი ზონის გარეთ",
                "საჩივარი",
            ],
        ),
        default_forbidden_rules=forbidden_rules(
            en=["Volume discounts or delivery costs that are not in the profile"],
            ru=["Скидки за объём или стоимость доставки, которых нет в анкете"],
            ka=[
                "ფასდაკლება მოცულობაზე ან მიტანის ღირებულება, რომლებიც ანკეტაში არ არის"
            ],
        ),
        autotest_kinds=autotest_kinds(),
    )
