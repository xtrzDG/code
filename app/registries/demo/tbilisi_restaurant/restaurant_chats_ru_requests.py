"""Conversations of the demo restaurant in Russian: requests for the staff."""

from app.registries.demo import demo_tool_calls as calls
from app.registries.demo.demo_activity_builder import DemoActivityBuilder
from app.registries.demo.demo_lines import assistant, customer, staff
from app.registries.demo.tbilisi_restaurant.restaurant_foundation import HALL_TABLE
from app.schemas.constants.bookings import BookingStatus, LeadStatus, LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationRating, ConversationStatus
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.handoffs.prefixed_id import HandoffId

HELLO: str = "Здравствуйте! Я AI-ассистент ресторана «Mtsvane Ezo»."
TELEGRAM = ChannelKind.TELEGRAM
WHATSAPP = ChannelKind.WHATSAPP
WEB = ChannelKind.WEB_CHAT


def record_russian_request_chats(
    story: DemoActivityBuilder, guests: dict[str, ContactDocument]
) -> None:
    """A banquet and a corporate lead, a complaint and a cancellation."""

    clock, talk, desk = story.clock, story.talk, story.desk

    # Sergey plans his mother's jubilee: a banquet the manager works on.
    start = clock.past(-9, "11:40")
    event = clock.upcoming(12, "18:00")
    lead_id = LeadId()
    details = f"Юбилей 60 лет, ~40 гостей, отдельный зал, {clock.short_date(event)}"
    chat = talk.chat(
        guests["sergey"],
        TELEGRAM,
        start,
        [
            customer(
                f"Добрый день! Хотим отметить юбилей мамы {clock.short_date(event)}, "
                "человек 40. Есть отдельный зал? Бюджет — до 4 000 лари."
            ),
            assistant(
                f"{HELLO} Отдельный зал вмещает до 45 гостей, банкетное меню — "
                "от 15 человек. Точную стоимость и меню согласует менеджер. "
                "Оставьте, пожалуйста, телефон.",
                calls.search("банкет отдельный зал", [story.item("Банкетное меню")]),
            ),
            customer("Сергей, +995 555 66 77 88"),
            assistant(
                "Спасибо, Сергей! Передал заявку менеджеру — он свяжется с вами "
                "сегодня.",
                calls.lead(
                    lead_id,
                    LeadType.BANQUET,
                    details,
                    "Сергей",
                    "+995555667788",
                    str(clock.local_date_of(event)),
                    40,
                    "до 4 000 лари",
                ),
            ),
            staff(
                "Сергей, добрый день! Это Тамар, администратор. Зал на эту дату "
                "свободен. Отправила вам два варианта банкетного меню — посмотрите, "
                "пожалуйста 🙂",
                pause=3000,
            ),
            customer("Спасибо, посмотрю вечером и отпишусь", pause=900),
        ],
        rating=ConversationRating.GOOD,
        rated_by=story.owner_id,
    )
    desk.lead(
        guests["sergey"],
        LeadType.BANQUET,
        details,
        TELEGRAM,
        chat.created_at,
        status=LeadStatus.IN_PROGRESS,
        conversation=chat,
        requested_day=12,
        party_size=40,
        budget="до 4 000 лари",
        lead_id=lead_id,
    )

    # Maxim asks about a corporate party in December (new lead).
    start = clock.past(-1, "11:00")
    lead_id = LeadId()
    details = "Новогодний корпоратив IT-компании, ~30 человек, середина декабря"
    chat = talk.chat(
        guests["maxim"],
        WEB,
        start,
        [
            customer(
                "Добрый день! Ищем место для новогоднего корпоратива в середине "
                "декабря, около 30 человек. Можно с музыкой?"
            ),
            assistant(
                f"{HELLO} Отдельный зал вмещает до 45 гостей; по пятницам и "
                "субботам у нас живая музыка. Передам запрос менеджеру — он "
                "предложит даты и меню. Как с вами связаться?",
                calls.search("корпоратив зал музыка", [story.item("Банкетное меню")]),
            ),
            customer("Максим, +995 592 00 11 22"),
            assistant(
                "Спасибо, Максим! Заявку передал, менеджер позвонит в рабочее время.",
                calls.lead(
                    lead_id,
                    LeadType.CORPORATE,
                    details,
                    "Максим",
                    "+995592001122",
                    party_size=30,
                ),
            ),
        ],
        status=ConversationStatus.OPEN,
    )
    desk.lead(
        guests["maxim"],
        LeadType.CORPORATE,
        details,
        WEB,
        chat.last_message_at,
        conversation=chat,
        party_size=30,
        lead_id=lead_id,
    )

    # Irina complains about cold khinkali: an urgent handoff, still open.
    start = clock.past(-1, "22:05")
    handoff_id = HandoffId()
    summary = "Жалоба: хинкали подали холодными, ждали 40 минут; просит перезвонить"
    chat = talk.chat(
        guests["irina"],
        TELEGRAM,
        start,
        [
            customer(
                "Сидим у вас сейчас. Хинкали ждали 40 минут и принесли холодными. "
                "Очень разочарованы."
            ),
            assistant(
                "Мне очень жаль, Ирина. Я AI-ассистент ресторана и сразу передаю "
                "ваше сообщение администратору зала — он подойдёт к вашему столу.",
                calls.handoff(
                    handoff_id, HandoffReason.COMPLAINT, summary, HandoffUrgency.HIGH
                ),
            ),
            customer("Хорошо, ждём", pause=120),
        ],
        rating=ConversationRating.GOOD,
        rated_by=story.owner_id,
    )
    desk.handoff(
        chat,
        HandoffReason.COMPLAINT,
        summary,
        HandoffUrgency.HIGH,
        handoff_id=handoff_id,
    )

    # Artem books, then cancels the next morning.
    start = clock.past(-7, "12:00")
    visit = clock.at(-6, "19:00")
    booking_id = BookingId()
    confirmation = "Забронировано: завтра, 19:00, 4 гостя, на имя Артём."
    cancelled = "Бронь на 19:00 отменена. Будем рады видеть вас в другой раз!"
    chat = talk.chat(
        guests["artem"],
        WHATSAPP,
        start,
        [
            customer("Привет! Завтра в 19:00 на четверых есть место?"),
            assistant(
                f"{HELLO} Да, завтра в 19:00 стол в зале свободен. "
                "Бронирую на ваше имя?",
                calls.availability(clock, desk.resource(HALL_TABLE), visit, 4),
            ),
            customer("Да, Артём"),
            assistant(
                confirmation,
                calls.booking(
                    clock,
                    booking_id,
                    desk.resource(HALL_TABLE),
                    visit,
                    4,
                    "Артём",
                    "+77017654321",
                    confirmation,
                ),
            ),
            customer("Извините, планы поменялись — отмените, пожалуйста", pause=75600),
            assistant(
                cancelled,
                calls.cancellation(
                    clock, booking_id, desk.resource(HALL_TABLE), visit, 4, cancelled
                ),
            ),
        ],
    )
    desk.booking(
        guests["artem"],
        HALL_TABLE,
        visit,
        4,
        WHATSAPP,
        status=BookingStatus.CANCELLED,
        conversation=chat,
        booking_id=booking_id,
        made_at=clock.later(start, 3),
    )
