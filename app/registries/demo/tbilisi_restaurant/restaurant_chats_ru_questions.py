"""Conversations of the demo restaurant in Russian: questions."""

from app.registries.demo import demo_tool_calls as calls
from app.registries.demo.demo_activity_builder import DemoActivityBuilder
from app.registries.demo.demo_lines import assistant, customer
from app.registries.demo.tbilisi_restaurant.restaurant_menu import CAKE_QUESTION_TITLE
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import (
    ConversationRating,
    ConversationRatingReason,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.handoffs.prefixed_id import UnansweredQuestionId

HELLO: str = "Здравствуйте! Я AI-ассистент ресторана «Mtsvane Ezo»."
TELEGRAM = ChannelKind.TELEGRAM
WHATSAPP = ChannelKind.WHATSAPP
WEB = ChannelKind.WEB_CHAT


def record_russian_question_chats(
    story: DemoActivityBuilder, guests: dict[str, ContactDocument]
) -> None:
    clock, talk, desk = story.clock, story.talk, story.desk

    # Anna asks what the banquet menu costs.
    talk.chat(
        guests["anna"],
        TELEGRAM,
        clock.past(-25, "13:00"),
        [
            customer("Сколько стоит банкетное меню на человека?"),
            assistant(
                f"{HELLO} Банкетное меню — 95 лари на гостя: холодные закуски, два "
                "горячих, хинкали, десерт, вино и лимонады. От 15 гостей.",
                calls.price("банкетное меню", story.item("Банкетное меню")),
            ),
            customer("Спасибо, подумаем"),
        ],
    )

    # Pavel asks about parking late at night.
    talk.chat(
        guests["pavel"],
        WEB,
        clock.past(-17, "00:15"),
        [
            customer("Есть у вас парковка?"),
            assistant(
                f"{HELLO} Своей парковки нет. Рядом городская платная парковка на "
                "улице Котэ Абхази — 2 лари в час. Удобнее приехать на такси.",
                calls.search("парковка", [story.item("Есть ли парковка")]),
            ),
        ],
    )

    # Natalia asks about her own cake: recorded, later answered by the owner.
    start = clock.past(-12, "10:00")
    question_id = UnansweredQuestionId()
    question = "Можно ли прийти со своим тортом?"
    talk.chat(
        guests["natalia"],
        TELEGRAM,
        start,
        [
            customer("Можно ли прийти со своим тортом на день рождения?"),
            assistant(
                f"{HELLO} Точного ответа у меня пока нет — передал вопрос команде. "
                "Ответ можно уточнить по телефону +995 32 219 00 19.",
                calls.search("свой торт", []),
                calls.unanswered(question_id, question),
            ),
        ],
        rating=ConversationRating.BAD,
        rated_by=story.owner_id,
        rating_reason=ConversationRatingReason.WRONG_INFO,
    )
    desk.question(
        question,
        "ru",
        clock.past(-11, "19:30"),
        occurrences=3,
        answered_by=story.item(CAKE_QUESTION_TITLE).id,
        question_id=question_id,
    )

    # Igor compares prices of khinkali and wine.
    talk.chat(
        guests["igor"],
        WHATSAPP,
        clock.past(-28, "18:00"),
        [
            customer("Почём хинкали и бокал саперави?"),
            assistant(
                f"{HELLO} Хинкали с говядиной и свининой — 1,80 лари за штуку (от 5 "
                "штук). Саперави квеври — 14 лари за бокал, 65 лари за бутылку.",
                calls.price("хинкали", story.item("Хинкали с говядиной")),
                calls.price("саперави", story.item("Саперави")),
            ),
            customer("👍"),
        ],
    )

    # Alexey asks for vegan dishes.
    talk.chat(
        guests["alexey"],
        WEB,
        clock.past(-20, "12:30"),
        [
            customer("Что у вас есть для веганов?"),
            assistant(
                f"{HELLO} Веганские блюда: лобио в горшочке с мчади (14 лари) и пхали "
                "ассорти (16 лари, с грецким орехом). Грузинский салат подадим без "
                "заправки с орехом.",
                calls.search(
                    "веганские блюда",
                    [story.item("Лобио"), story.item("Пхали ассорти")],
                ),
            ),
        ],
    )
