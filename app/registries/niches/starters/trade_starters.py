"""Starter answers of online shops and B2B suppliers (orders, not bookings)."""

from app.registries.niches.starters.starter_parts import (
    at,
    offer,
    open_faq,
    opening,
    ready_faq,
    text,
)
from app.schemas.constants.knowledge import KnowledgeItemKind as Kind
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.setup.starter_catalog import NicheStarterDefinition

ONLINE_SHOP_STARTERS = NicheStarterDefinition(
    niche_key=NicheKey.ONLINE_SHOP,
    opening=opening((at(10), at(19)), None),
    tones=text(
        (
            "Friendly and helpful, short answers",
            "Дружелюбный и полезный, короткие ответы",
            "მეგობრული და დამხმარე, მოკლე პასუხები",
        )
    ),
    faq=[
        ready_faq(
            "how_to_order",
            (
                "How do I place an order?",
                "Как оформить заказ?",
                "როგორ გავაფორმო შეკვეთა?",
            ),
            (
                "Write the products and quantity, your name, phone number and "
                "delivery address here, and I will pass the order to our team.",
                "Напишите здесь товары и количество, имя, телефон и адрес доставки — "
                "я передам заказ команде.",
                "დაწერეთ აქ პროდუქტები და რაოდენობა, სახელი, ტელეფონის ნომერი და "
                "მიტანის მისამართი — შეკვეთას ჩვენს გუნდს გადავცემ.",
            ),
        ),
        ready_faq(
            "order_status",
            (
                "Where is my order?",
                "Где мой заказ?",
                "სად არის ჩემი შეკვეთა?",
            ),
            (
                "Write your order number or the phone number you ordered with here, "
                "and I will pass your question to our team.",
                "Напишите здесь номер заказа или телефон, на который оформляли, — я "
                "передам вопрос команде.",
                "დაწერეთ აქ შეკვეთის ნომერი ან ტელეფონი, რომლითაც შეუკვეთეთ — თქვენს "
                "კითხვას გუნდს გადავცემ.",
            ),
        ),
        open_faq(
            "delivery_time",
            (
                "How long does delivery take?",
                "Сколько идёт доставка?",
                "რამდენ ხანში მოდის მიტანა?",
            ),
        ),
        open_faq(
            "returns",
            (
                "Can I return an item?",
                "Можно ли вернуть товар?",
                "შეიძლება ნივთის დაბრუნება?",
            ),
        ),
    ],
    offers=[
        offer(
            "bestseller", Kind.PRODUCT, ("Our bestseller", "Хит продаж", "ბესტსელერი")
        ),
        offer(
            "gift_set",
            Kind.PRODUCT,
            ("Gift set", "Подарочный набор", "სასაჩუქრე ნაკრები"),
        ),
        offer("new_arrival", Kind.PRODUCT, ("New arrival", "Новинка", "სიახლე")),
    ],
)

B2B_SUPPLY_STARTERS = NicheStarterDefinition(
    niche_key=NicheKey.B2B_SUPPLY,
    opening=opening((at(9), at(18)), None),
    tones=text(
        (
            "Businesslike and precise",
            "Деловой и точный",
            "საქმიანი და ზუსტი",
        )
    ),
    faq=[
        ready_faq(
            "wholesale_order",
            (
                "How do I place a wholesale order?",
                "Как сделать оптовый заказ?",
                "როგორ გავაკეთო საბითუმო შეკვეთა?",
            ),
            (
                "Write the products, quantities, your company name and contact "
                "details here, and our manager will prepare an offer.",
                "Напишите здесь товары, количество, название компании и контакты — "
                "менеджер подготовит предложение.",
                "დაწერეთ აქ პროდუქტები, რაოდენობა, კომპანიის სახელი და საკონტაქტო "
                "მონაცემები — მენეჯერი შეთავაზებას მოგიმზადებთ.",
            ),
        ),
        ready_faq(
            "price_list",
            (
                "Can I get your price list?",
                "Можно получить прайс-лист?",
                "შეიძლება ფასების სიის მიღება?",
            ),
            (
                "Yes. Write your company name and e-mail here, and our manager will "
                "send the current price list.",
                "Да. Напишите здесь название компании и e-mail — менеджер пришлёт "
                "актуальный прайс-лист.",
                "დიახ. დაწერეთ აქ კომპანიის სახელი და ელფოსტა — მენეჯერი "
                "გამოგიგზავნით მიმდინარე ფასების სიას.",
            ),
        ),
        open_faq(
            "minimum_order",
            (
                "What is the minimum order?",
                "Какой минимальный заказ?",
                "რა არის მინიმალური შეკვეთა?",
            ),
        ),
        open_faq(
            "delivery_terms",
            (
                "Do you deliver, and on what terms?",
                "Есть ли доставка и на каких условиях?",
                "გაქვთ მიტანა და რა პირობებით?",
            ),
        ),
    ],
    offers=[
        offer(
            "bulk_pack",
            Kind.PRODUCT,
            ("Bulk pack", "Оптовая упаковка", "საბითუმო შეფუთვა"),
        ),
        offer(
            "regular_supply",
            Kind.SERVICE,
            (
                "Regular supply contract",
                "Договор регулярных поставок",
                "რეგულარული მიწოდების ხელშეკრულება",
            ),
        ),
        offer(
            "sample_kit",
            Kind.PRODUCT,
            ("Sample kit", "Набор образцов", "ნიმუშების ნაკრები"),
        ),
    ],
)
