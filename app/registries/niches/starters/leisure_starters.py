"""Starter answers of event venues, entertainment and fitness."""

from app.registries.niches.starters.starter_parts import (
    CHANGE_APPOINTMENT,
    CHANGE_RESERVATION,
    NOTICE_THREE_HOURS,
    at,
    booking,
    offer,
    open_faq,
    opening,
    ready_faq,
    resource,
    text,
)
from app.schemas.constants.knowledge import KnowledgeItemKind as Kind
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.setup.starter_catalog import NicheStarterDefinition

EVENT_VENUE_STARTERS = NicheStarterDefinition(
    niche_key=NicheKey.EVENT_VENUE,
    opening=opening((at(10), at(20)), (at(11), at(18))),
    booking=booking(
        240,
        100,
        2880,
        (
            "Please tell us about changes at least 14 days before the event.",
            "Пожалуйста, сообщайте об изменениях не позже чем за 14 дней до "
            "мероприятия.",
            "გთხოვთ, ცვლილებების შესახებ შეგვატყობინოთ ღონისძიებამდე მინიმუმ 14 "
            "დღით ადრე.",
        ),
    ),
    resource=resource(("Main hall", "Большой зал", "დიდი დარბაზი"), 100, 1),
    tones=text(
        (
            "Professional and friendly, focused on the guest's event",
            "Профессиональный и дружелюбный, с вниманием к событию гостя",
            "პროფესიონალური და მეგობრული, ყურადღებით სტუმრის ღონისძიებაზე",
        )
    ),
    faq=[
        ready_faq(
            "book_event",
            (
                "How do I book the hall for an event?",
                "Как забронировать зал на мероприятие?",
                "როგორ დავჯავშნო დარბაზი ღონისძიებისთვის?",
            ),
            (
                "Write the date, the number of guests and the kind of event here. I "
                "will check the date and pass the details to our manager.",
                "Напишите здесь дату, количество гостей и формат мероприятия — я "
                "проверю дату и передам детали менеджеру.",
                "დაწერეთ აქ თარიღი, სტუმრების რაოდენობა და ღონისძიების ტიპი — "
                "შევამოწმებ თარიღს და დეტალებს მენეჯერს გადავცემ.",
            ),
        ),
        ready_faq(
            "visit_hall",
            (
                "Can I come and see the hall?",
                "Можно ли приехать посмотреть зал?",
                "შეიძლება მოვიდე და დარბაზი ვნახო?",
            ),
            (
                "Yes. Write a convenient day and time here, and I will arrange a visit "
                "with our manager.",
                "Да. Напишите здесь удобные день и время — я договорюсь о визите с "
                "менеджером.",
                "დიახ. დაწერეთ აქ თქვენთვის მოსახერხებელი დღე და დრო — ვიზიტს "
                "მენეჯერთან შევათანხმებ.",
            ),
        ),
        open_faq(
            "own_drinks",
            (
                "Can we bring our own drinks?",
                "Можно ли принести свои напитки?",
                "შეიძლება საკუთარი სასმელის მოტანა?",
            ),
        ),
        open_faq(
            "decoration",
            (
                "Do you help with decoration?",
                "Помогаете ли вы с оформлением?",
                "გვეხმარებით მორთვაში?",
            ),
        ),
    ],
    offers=[
        offer(
            "banquet_package",
            Kind.PACKAGE,
            (
                "Banquet package per guest",
                "Банкетный пакет на гостя",
                "საბანკეტო პაკეტი ერთ სტუმარზე",
            ),
        ),
        offer(
            "hall_rental",
            Kind.SERVICE,
            ("Hall rental per hour", "Аренда зала за час", "დარბაზის ქირა საათში"),
            60,
        ),
        offer(
            "hall_decoration",
            Kind.SERVICE,
            ("Hall decoration", "Оформление зала", "დარბაზის მორთვა"),
        ),
    ],
)

ENTERTAINMENT_STARTERS = NicheStarterDefinition(
    niche_key=NicheKey.ENTERTAINMENT,
    opening=opening((at(11), at(22)), (at(10), at(23))),
    booking=booking(60, 10, 60, NOTICE_THREE_HOURS),
    resource=resource(("Game room", "Игровой зал", "სათამაშო დარბაზი"), 10, 1),
    tones=text(
        (
            "Energetic and friendly",
            "Энергичный и дружелюбный",
            "ენერგიული და მეგობრული",
        )
    ),
    faq=[
        ready_faq(
            "book_session",
            (
                "How do I book a session?",
                "Как забронировать игру?",
                "როგორ დავჯავშნო თამაში?",
            ),
            (
                "Write the date, time and number of players here, and I will book it "
                "for you.",
                "Напишите здесь дату, время и количество игроков — я забронирую.",
                "დაწერეთ აქ თარიღი, დრო და მოთამაშეების რაოდენობა — დაგიჯავშნით.",
            ),
        ),
        CHANGE_RESERVATION,
        open_faq(
            "age_limit",
            (
                "From what age can children play?",
                "С какого возраста можно детям?",
                "რა ასაკიდან შეუძლიათ ბავშვებს თამაში?",
            ),
        ),
        open_faq(
            "birthday",
            (
                "Do you host birthday parties?",
                "Проводите ли вы дни рождения?",
                "ატარებთ დაბადების დღეებს?",
            ),
        ),
    ],
    offers=[
        offer(
            "one_hour_session",
            Kind.SERVICE,
            ("One-hour session", "Сеанс на час", "ერთსაათიანი სეანსი"),
            60,
        ),
        offer(
            "birthday_party",
            Kind.PACKAGE,
            (
                "Birthday party package",
                "Пакет «День рождения»",
                "დაბადების დღის პაკეტი",
            ),
        ),
        offer(
            "group_game",
            Kind.PACKAGE,
            (
                "Group game for up to 10 players",
                "Игра для группы до 10 человек",
                "ჯგუფური თამაში 10 მოთამაშემდე",
            ),
        ),
    ],
)

FITNESS_STARTERS = NicheStarterDefinition(
    niche_key=NicheKey.FITNESS,
    opening=opening((at(7), at(22)), (at(9), at(20))),
    booking=booking(
        60,
        2,
        60,
        (
            "Please cancel at least 6 hours before the class.",
            "Пожалуйста, отменяйте запись не позже чем за 6 часов до занятия.",
            "გთხოვთ, ჩაწერა გააუქმოთ ვარჯიშამდე მინიმუმ 6 საათით ადრე.",
        ),
    ),
    resource=resource(("Group class", "Групповое занятие", "ჯგუფური ვარჯიში"), 15, 1),
    tones=text(
        (
            "Energetic and motivating, short answers",
            "Энергичный и мотивирующий, короткие ответы",
            "ენერგიული და მოტივაციური, მოკლე პასუხები",
        )
    ),
    faq=[
        ready_faq(
            "book_class",
            (
                "How do I sign up for a class?",
                "Как записаться на занятие?",
                "როგორ ჩავეწერო ვარჯიშზე?",
            ),
            (
                "Write the class and a convenient day and time here, and I will sign "
                "you up.",
                "Напишите здесь, на какое занятие и в какие день и время удобно, — я "
                "вас запишу.",
                "დაწერეთ აქ, რომელ ვარჯიშზე და რომელ დღეს და დროს გსურთ — ჩაგწერთ.",
            ),
        ),
        CHANGE_APPOINTMENT,
        open_faq(
            "trial_class",
            (
                "Is there a free trial class?",
                "Есть ли бесплатное пробное занятие?",
                "არის უფასო საცდელი ვარჯიში?",
            ),
        ),
        open_faq(
            "showers",
            (
                "Are there showers and lockers?",
                "Есть ли душ и шкафчики?",
                "არის შხაპი და კარადები?",
            ),
        ),
    ],
    offers=[
        offer(
            "monthly_membership",
            Kind.PACKAGE,
            ("Monthly membership", "Абонемент на месяц", "ერთთვიანი აბონემენტი"),
        ),
        offer(
            "single_visit",
            Kind.SERVICE,
            ("Single visit", "Разовое посещение", "ერთჯერადი ვიზიტი"),
            60,
        ),
        offer(
            "personal_training",
            Kind.SERVICE,
            ("Personal training", "Персональная тренировка", "პერსონალური ვარჯიში"),
            60,
        ),
    ],
)
