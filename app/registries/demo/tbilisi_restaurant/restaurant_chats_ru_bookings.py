"""Conversations of the demo restaurant in Russian: bookings."""

from app.registries.demo import demo_tool_calls as calls
from app.registries.demo.demo_activity_builder import DemoActivityBuilder
from app.registries.demo.demo_lines import assistant, customer
from app.registries.demo.demo_words import day_word
from app.registries.demo.tbilisi_restaurant.restaurant_foundation import (
    COURTYARD_TABLE,
    HALL_TABLE,
    LONG_TABLE,
    WINDOW_TABLE,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationRating, ConversationStatus
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.bookings.prefixed_id import BookingId

HELLO: str = "Здравствуйте! Я ИИ-ассистент ресторана «Мцване Эзо»."
TELEGRAM = ChannelKind.TELEGRAM
WHATSAPP = ChannelKind.WHATSAPP
WEB = ChannelKind.WEB_CHAT


def record_russian_booking_chats(
    story: DemoActivityBuilder, guests: dict[str, ContactDocument]
) -> None:
    """Russian-speaking guests booking, coming, not coming and cancelling."""

    clock, talk, desk = story.clock, story.talk, story.desk

    # Anna books a window table for two; they came.
    start = clock.past(-2, "10:20")
    visit = clock.at(-1, "20:00")
    booking_id = BookingId()
    confirmation = "Готово! Завтра, 20:00, стол у окна на двоих, на имя Анна."
    chat = talk.chat(
        guests["anna"],
        TELEGRAM,
        start,
        [
            customer("Добрый день! Можно столик у окна на завтра на 20:00, нас двое?"),
            assistant(
                f"{HELLO} Да, завтра в 20:00 стол у окна свободен. "
                "Записать на ваше имя?",
                calls.availability(clock, desk.resource(WINDOW_TABLE), visit, 2),
            ),
            customer("Да, Анна. Спасибо!"),
            assistant(
                f"{confirmation} Стол держим 15 минут. Хорошего вечера!",
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(WINDOW_TABLE),
                    visit,
                    2,
                    "Анна",
                    "+79161234567",
                    confirmation,
                ),
            ),
        ],
        rating=ConversationRating.GOOD,
        rated_by=story.team_member_id,
    )
    desk.booking(
        guests["anna"],
        WINDOW_TABLE,
        visit,
        2,
        TELEGRAM,
        status=BookingStatus.COMPLETED,
        conversation=chat,
        booking_id=booking_id,
    )

    # Dmitry wants the courtyard for six tonight and asks about heaters.
    start = clock.ago(hours=3, minutes=5)
    slot = clock.next_slot(("21:00", "20:30", "14:00", "13:30"))
    day, time = day_word(clock, slot, "ru", said_at=start), clock.clock_of(slot)
    booking_id = BookingId()
    confirmation = f"Готово: {day} в {time}, двор, 6 гостей, на имя Дмитрий."
    chat = talk.chat(
        guests["dmitry"],
        WHATSAPP,
        start,
        [
            customer(f"Здравствуйте, есть стол во дворе на 6 человек {day} на {time}?"),
            assistant(
                f"{HELLO} Да, {day} в {time} во дворе свободен стол на шестерых.",
                calls.availability(clock, desk.resource(COURTYARD_TABLE), slot, 6),
            ),
            customer("Вечером не холодно будет? С нами пожилые родители"),
            assistant(
                "Во дворе с октября работают уличные обогреватели, есть пледы. "
                "Если станет прохладно — пересадим в зал. Бронирую?",
                calls.search("обогреватели во дворе", [story.item("Есть ли обогрев")]),
            ),
            customer("Да, на Дмитрия"),
            assistant(
                f"{confirmation} До встречи!",
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(COURTYARD_TABLE),
                    slot,
                    6,
                    "Дмитрий",
                    "+79035556677",
                    confirmation,
                ),
            ),
        ],
        status=ConversationStatus.OPEN,
    )
    desk.booking(
        guests["dmitry"],
        COURTYARD_TABLE,
        slot,
        6,
        WHATSAPP,
        conversation=chat,
        booking_id=booking_id,
    )

    # Elena books lunch with a child on the website.
    start = clock.past(-1, "14:10")
    visit = clock.upcoming(1, "13:00")
    day = day_word(clock, visit, "ru", said_at=start)
    booking_id = BookingId()
    confirmation = f"Забронировано: {day}, 13:00, 3 гостя, детский стул, на имя Елена."
    chat = talk.chat(
        guests["elena"],
        WEB,
        start,
        [
            customer(
                f"Добрый день! Хотим прийти {day} в 13:00, двое взрослых и "
                "ребёнок 4 лет."
            ),
            assistant(
                f"{HELLO} Будем рады! Есть детские стулья и детское меню — "
                "куриные котлетки с пюре. Стол в зале свободен. Как вас записать?",
                calls.availability(clock, desk.resource(HALL_TABLE), visit, 3),
                calls.search(
                    "дети детское меню", [story.item("Можно ли прийти с детьми")]
                ),
            ),
            customer("Елена, +995 591 77 88 99"),
            assistant(
                f"{confirmation} Детский стул поставим заранее.",
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(HALL_TABLE),
                    visit,
                    3,
                    "Елена",
                    "+995591778899",
                    confirmation,
                ),
            ),
        ],
    )
    desk.booking(
        guests["elena"],
        HALL_TABLE,
        visit,
        3,
        WEB,
        conversation=chat,
        notes="Ребёнок 4 лет, нужен детский стул",
        booking_id=booking_id,
    )

    # Olga books for three and does not come.
    start = clock.past(-4, "16:00")
    visit = clock.at(-3, "21:00")
    booking_id = BookingId()
    confirmation = "Готово: завтра, 21:00, 3 гостя, на имя Ольга."
    chat = talk.chat(
        guests["olga"],
        WHATSAPP,
        start,
        [
            customer("Добрый вечер, на завтра на 21:00 на троих можно?"),
            assistant(
                f"{HELLO} Да, завтра в 21:00 есть стол в зале. На чьё имя?",
                calls.availability(clock, desk.resource(HALL_TABLE), visit, 3),
            ),
            customer("Ольга"),
            assistant(
                confirmation,
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(HALL_TABLE),
                    visit,
                    3,
                    "Ольга",
                    "+375291112233",
                    confirmation,
                ),
            ),
        ],
    )
    desk.booking(
        guests["olga"],
        HALL_TABLE,
        visit,
        3,
        WHATSAPP,
        status=BookingStatus.NO_SHOW,
        conversation=chat,
        booking_id=booking_id,
    )

    # Victoria books the long table for a birthday with her own cake.
    start = clock.ago(hours=5, minutes=20)
    visit = clock.upcoming(4, "20:00")
    day = day_word(clock, visit, "ru", said_at=start)
    booking_id = BookingId()
    confirmation = (
        f"Забронировано: большой стол {day} в 20:00, 8 гостей, на имя Виктория."
    )
    chat = talk.chat(
        guests["victoria"],
        WEB,
        start,
        [
            customer(
                f"Здравствуйте! {day.capitalize()} у мужа день рождения, нас "
                "8 человек, "
                "к 20:00. И можно ли принести свой торт?"
            ),
            assistant(
                f"{HELLO} Поздравляем! Большой стол на 10 гостей свободен. Свой торт "
                "можно: сервисный сбор 15 лари — подадим на тарелках и зажжём свечи 🎂 "
                "Для компаний от 8 гостей нужна предоплата 20 %, менеджер пришлёт "
                "ссылку. Бронирую?",
                calls.availability(clock, desk.resource(LONG_TABLE), visit, 8),
                calls.search("свой торт", [story.item("Можно прийти со своим")]),
            ),
            customer("Да, Виктория"),
            assistant(
                confirmation,
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(LONG_TABLE),
                    visit,
                    8,
                    "Виктория",
                    None,
                    confirmation,
                ),
            ),
        ],
        status=ConversationStatus.OPEN,
    )
    desk.booking(
        guests["victoria"],
        LONG_TABLE,
        visit,
        8,
        WEB,
        conversation=chat,
        notes="День рождения, свой торт (сбор 15 лари), предоплата 20 %",
        booking_id=booking_id,
    )
