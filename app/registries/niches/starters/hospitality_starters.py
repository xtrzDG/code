"""Starter answers of restaurants, hotels, short-term rentals and event venues."""

from app.registries.niches.starters.starter_parts import (
    CHANGE_RESERVATION,
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

RESTAURANT_STARTERS = NicheStarterDefinition(
    niche_key=NicheKey.RESTAURANT,
    opening=opening((at(12), at(23)), (at(12), at(23))),
    booking=booking(
        120,
        8,
        60,
        (
            "Please let us know at least 2 hours in advance if your plans change.",
            "Если планы изменятся, предупредите нас, пожалуйста, хотя бы за 2 часа.",
            "თუ გეგმები შეგეცვლებათ, გთხოვთ, გაგვაფრთხილოთ მინიმუმ 2 საათით ადრე.",
        ),
    ),
    resource=resource(("Table", "Стол", "მაგიდა"), 4, 10),
    tones=text(
        (
            "Warm and welcoming, short answers",
            "Тёплый и гостеприимный, короткие ответы",
            "თბილი და სტუმართმოყვარე, მოკლე პასუხები",
        )
    ),
    faq=[
        ready_faq(
            "book_table",
            (
                "How can I book a table?",
                "Как забронировать стол?",
                "როგორ დავჯავშნო მაგიდა?",
            ),
            (
                "Write the date, time and number of guests right here, and I will "
                "book a table for you.",
                "Напишите здесь дату, время и количество гостей — я забронирую стол.",
                "დაწერეთ აქ თარიღი, დრო და სტუმრების რაოდენობა — მაგიდას დაგიჯავშნით.",
            ),
        ),
        CHANGE_RESERVATION,
        open_faq(
            "parking",
            (
                "Is there parking nearby?",
                "Есть ли рядом парковка?",
                "არის ახლოს პარკინგი?",
            ),
        ),
        open_faq(
            "pets",
            (
                "Can I come with a dog?",
                "Можно ли прийти с собакой?",
                "შეიძლება ძაღლით მოსვლა?",
            ),
        ),
    ],
    offers=[
        offer(
            "signature_dish",
            Kind.MENU_ITEM,
            ("Chef's signature dish", "Фирменное блюдо шефа", "შეფის ფირმული კერძი"),
        ),
        offer(
            "business_lunch",
            Kind.PACKAGE,
            ("Business lunch", "Бизнес-ланч", "ბიზნეს-ლანჩი"),
        ),
        offer(
            "dessert_of_the_day",
            Kind.MENU_ITEM,
            ("Dessert of the day", "Десерт дня", "დღის დესერტი"),
        ),
    ],
)

HOTEL_STARTERS = NicheStarterDefinition(
    niche_key=NicheKey.HOTEL,
    opening=opening((at(0), at(24)), (at(0), at(24))),
    booking=booking(
        None,
        4,
        0,
        (
            "Please cancel or change your booking at least 48 hours before arrival.",
            "Пожалуйста, отменяйте или меняйте бронь не позже чем за 48 часов до "
            "заезда.",
            "გთხოვთ, ჯავშანი გააუქმოთ ან შეცვალოთ ჩამოსვლამდე მინიმუმ 48 საათით ადრე.",
        ),
    ),
    resource=resource(
        (
            "Standard double room",
            "Стандартный двухместный номер",
            "სტანდარტული ორადგილიანი ოთახი",
        ),
        2,
        5,
    ),
    tones=text(
        (
            "Polite and attentive, like a good receptionist",
            "Вежливый и внимательный, как хороший администратор",
            "თავაზიანი და ყურადღებიანი, როგორც კარგი ადმინისტრატორი",
        )
    ),
    faq=[
        ready_faq(
            "book_room",
            (
                "How can I book a room?",
                "Как забронировать номер?",
                "როგორ დავჯავშნო ოთახი?",
            ),
            (
                "Write your arrival and departure dates and the number of guests "
                "here, and I will check what is free and book it.",
                "Напишите здесь даты заезда и выезда и количество гостей — я проверю "
                "свободные номера и забронирую.",
                "დაწერეთ აქ ჩამოსვლისა და წასვლის თარიღები და სტუმრების რაოდენობა — "
                "შევამოწმებ თავისუფალ ოთახებს და დაგიჯავშნით.",
            ),
        ),
        CHANGE_RESERVATION,
        open_faq(
            "check_in_time",
            (
                "What time are check-in and check-out?",
                "Во сколько заезд и выезд?",
                "რომელ საათზეა შესახლება და გამოსახლება?",
            ),
        ),
        open_faq(
            "breakfast",
            (
                "Is breakfast included?",
                "Завтрак включён?",
                "საუზმე შედის ფასში?",
            ),
        ),
    ],
    offers=[
        offer(
            "standard_room",
            Kind.ROOM_TYPE,
            (
                "Standard double room",
                "Стандартный двухместный номер",
                "სტანდარტული ორადგილიანი ოთახი",
            ),
        ),
        offer(
            "family_room",
            Kind.ROOM_TYPE,
            ("Family room", "Семейный номер", "საოჯახო ოთახი"),
        ),
        offer(
            "airport_transfer",
            Kind.SERVICE,
            ("Airport transfer", "Трансфер из аэропорта", "ტრანსფერი აეროპორტიდან"),
        ),
    ],
)

SHORT_TERM_RENTAL_STARTERS = NicheStarterDefinition(
    niche_key=NicheKey.SHORT_TERM_RENTAL,
    opening=opening((at(9), at(21)), (at(9), at(21))),
    booking=booking(
        None,
        4,
        0,
        (
            "Please cancel at least 3 days before arrival.",
            "Пожалуйста, отменяйте бронь не позже чем за 3 дня до заезда.",
            "გთხოვთ, ჯავშანი გააუქმოთ ჩამოსვლამდე მინიმუმ 3 დღით ადრე.",
        ),
    ),
    resource=resource(("Apartment", "Квартира", "ბინა"), 4, 1),
    tones=text(
        (
            "Friendly and helpful, like a good host",
            "Дружелюбный и заботливый, как хороший хозяин",
            "მეგობრული და მზრუნველი, როგორც კარგი მასპინძელი",
        )
    ),
    faq=[
        ready_faq(
            "book_stay",
            (
                "How can I book the apartment?",
                "Как забронировать квартиру?",
                "როგორ დავჯავშნო ბინა?",
            ),
            (
                "Write your dates and the number of guests here, and I will check "
                "whether it is free and book it.",
                "Напишите здесь даты и количество гостей — я проверю, свободна ли "
                "квартира, и забронирую.",
                "დაწერეთ აქ თარიღები და სტუმრების რაოდენობა — შევამოწმებ, თავისუფალია "
                "თუ არა ბინა, და დაგიჯავშნით.",
            ),
        ),
        CHANGE_RESERVATION,
        open_faq(
            "check_in",
            (
                "How does check-in work?",
                "Как происходит заселение?",
                "როგორ ხდება შესახლება?",
            ),
        ),
        open_faq(
            "amenities",
            (
                "Is there Wi-Fi and a washing machine?",
                "Есть ли Wi-Fi и стиральная машина?",
                "არის Wi-Fi და სარეცხი მანქანა?",
            ),
        ),
    ],
    offers=[
        offer(
            "whole_apartment",
            Kind.ROOM_TYPE,
            (
                "Whole apartment for up to 4 guests",
                "Квартира целиком до 4 гостей",
                "მთლიანი ბინა 4 სტუმრამდე",
            ),
        ),
        offer(
            "late_checkout",
            Kind.SERVICE,
            ("Late check-out", "Поздний выезд", "გვიანი გამოსახლება"),
        ),
        offer(
            "airport_pickup",
            Kind.SERVICE,
            ("Airport pick-up", "Встреча в аэропорту", "აეროპორტში დახვედრა"),
        ),
    ],
)
