"""Menu, packages, FAQ and policies of the Tbilisi demo restaurant (in Russian,
the owner's language; the assistant answers in the guest's language)."""

from functools import partial

from typed_time_provider import Microseconds

from app.registries.demo.demo_foundation_parts import knowledge_item
from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument

DISH = KnowledgeItemKind.MENU_ITEM
# Answered from an unanswered question ("own birthday cake?").
CAKE_QUESTION_TITLE: str = "Можно прийти со своим тортом?"


def build_restaurant_knowledge(
    business: BusinessDocument, since: Microseconds
) -> list[KnowledgeItemDocument]:
    item = partial(knowledge_item, business, since=since)
    return [
        item(
            DISH,
            "Хачапури по-аджарски (აჭარული ხაჭაპური)",
            price_minor=2200,
            body="Лодочка из теста с сулугуни, яйцом и сливочным маслом. "
            "Готовим 20 минут.",
            tags=["bestseller", "bakery"],
        ),
        item(
            DISH,
            "Хачапури по-имеретински",
            price_minor=1800,
            body="Круглый, с имеретинским сыром внутри. На 2–3 человек.",
        ),
        item(
            DISH,
            "Хинкали с говядиной и свининой",
            price_minor=180,
            body="Цена за 1 штуку, заказ от 5 штук. Варим 15 минут.",
            tags=["bestseller"],
        ),
        item(
            DISH,
            "Хинкали с грибами и сулугуни",
            price_minor=170,
            body="Цена за 1 штуку, заказ от 5 штук.",
            tags=["vegetarian"],
        ),
        item(
            DISH,
            "Мцвади из свиной шеи",
            price_minor=2600,
            body="Шашлык на виноградной лозе, с маринованным луком и ткемали.",
        ),
        item(
            DISH,
            "Чкмерули",
            price_minor=3400,
            body="Цыплёнок в сливочно-чесночном соусе, подаём в глиняной кеци.",
        ),
        item(
            DISH,
            "Чакапули",
            price_minor=3200,
            body="Телятина с тархуном, ткемали и белым вином.",
            attributes=[("season", "осень")],
        ),
        item(
            DISH,
            "Пхали ассорти",
            price_minor=1600,
            body="Шпинат, свёкла и стручковая фасоль с грецким орехом. Содержит орехи.",
            tags=["vegetarian", "vegan", "nuts"],
        ),
        item(
            DISH,
            "Бадриджани с ореховой пастой",
            price_minor=1500,
            body="Рулетики из баклажана с орехом и гранатом. Содержит орехи.",
            tags=["vegetarian", "nuts"],
        ),
        item(
            DISH,
            "Лобио в горшочке с мчади",
            price_minor=1400,
            body="Красная фасоль с травами, кукурузная лепёшка.",
            tags=["vegan"],
        ),
        item(
            DISH,
            "Грузинский салат с ореховой заправкой",
            price_minor=1400,
            body="Томаты, огурцы, красный лук, кинза. Можно без орехов.",
            tags=["vegetarian"],
        ),
        item(
            DISH,
            "Детское меню: куриные котлетки с пюре",
            price_minor=1500,
            body="Для гостей до 10 лет; есть детские стулья.",
            tags=["kids"],
        ),
        item(
            DISH,
            "Чурчхела домашняя",
            price_minor=600,
            body="Кахетинская, с грецким орехом.",
            tags=["dessert", "nuts"],
        ),
        item(
            DISH,
            "Саперави квеври, бокал 150 мл",
            price_minor=1400,
            body="Сухое красное, Кахети. Бутылка — 65 лари.",
            tags=["wine"],
        ),
        item(
            DISH,
            "Ркацители квеври, бокал 150 мл",
            price_minor=1300,
            body="Оранжевое вино, Кахети. Бутылка — 60 лари.",
            tags=["wine"],
        ),
        item(DISH, "Домашний тархуновый лимонад, 0,5 л", price_minor=700),
        item(
            KnowledgeItemKind.PACKAGE,
            "Банкетное меню (на гостя)",
            price_minor=9500,
            body="Холодные закуски, два горячих, хинкали, десерт, вино и лимонады. "
            "От 15 гостей, в отдельном зале до 45 гостей.",
        ),
        item(
            KnowledgeItemKind.PACKAGE,
            "Праздничный сет «Супра» на 4 гостей",
            price_minor=22000,
            body="Пхали, хачапури, мцвади, хинкали (20 шт.), чурчхела и бутылка вина.",
        ),
        item(
            KnowledgeItemKind.FAQ,
            "Есть ли парковка?",
            body="Своей парковки нет. Рядом городская платная парковка на улице "
            "Котэ Абхази — 2 лари в час. Удобнее приехать на такси.",
            source=KnowledgeItemSource.PROFILE,
        ),
        item(
            KnowledgeItemKind.FAQ,
            "Можно ли прийти с детьми?",
            body="Да: есть детские стулья, детское меню и закрытый двор.",
            source=KnowledgeItemSource.PROFILE,
        ),
        item(
            KnowledgeItemKind.FAQ,
            "Когда у вас живая музыка?",
            body="По пятницам и субботам с 20:00 — гитара и грузинское многоголосие.",
            source=KnowledgeItemSource.PROFILE,
        ),
        item(
            KnowledgeItemKind.FAQ,
            "Есть ли доставка?",
            body="Доставляем через Wolt и Glovo по Тбилиси, ссылка — в разделе "
            "доставки.",
            source=KnowledgeItemSource.PROFILE,
        ),
        item(
            KnowledgeItemKind.FAQ,
            "Как можно оплатить?",
            body="Картами Visa и Mastercard, Apple Pay, Google Pay и наличными в лари.",
            source=KnowledgeItemSource.PROFILE,
        ),
        item(
            KnowledgeItemKind.FAQ,
            "Есть ли обогреватели во дворе?",
            body="Да, с октября во дворе работают уличные обогреватели и есть пледы.",
            source=KnowledgeItemSource.PROFILE,
        ),
        item(
            KnowledgeItemKind.FAQ,
            CAKE_QUESTION_TITLE,
            body="Да, свой торт можно. Сервисный сбор — 15 лари: подадим на тарелках, "
            "зажжём свечи.",
            source=KnowledgeItemSource.UNANSWERED_QUESTION,
        ),
        item(
            KnowledgeItemKind.POLICY,
            "Правила брони",
            body="Стол держим 15 минут. Для компаний от 8 гостей — предоплата 20 %. "
            "Бесплатная отмена — за 3 часа до визита.",
        ),
        item(
            KnowledgeItemKind.POLICY,
            "Сервисный сбор",
            body="10 % к счёту для компаний от 6 гостей.",
        ),
    ]
