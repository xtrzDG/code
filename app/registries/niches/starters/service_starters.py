"""Starter answers of car services, car rentals and tours, and home services."""

from app.registries.niches.starters.starter_parts import (
    CHANGE_RESERVATION,
    NOTICE_THREE_HOURS,
    NOTICE_TWELVE_HOURS,
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

CAR_SERVICE_STARTERS = NicheStarterDefinition(
    niche_key=NicheKey.CAR_SERVICE,
    opening=opening((at(9), at(19)), (at(10), at(16))),
    booking=booking(60, 1, 120, NOTICE_THREE_HOURS),
    resource=resource(("Service bay", "Ремонтный пост", "სარემონტო ბოქსი"), 1, 2),
    tones=text(
        (
            "Clear and practical, no jargon",
            "Чётко и по делу, без жаргона",
            "მკაფიოდ და საქმიანად, ჟარგონის გარეშე",
        )
    ),
    faq=[
        ready_faq(
            "book_service",
            (
                "How do I book my car in?",
                "Как записать машину на сервис?",
                "როგორ ჩავწერო მანქანა სერვისზე?",
            ),
            (
                "Write the car make and model, what needs doing and a convenient day "
                "and time here, and I will book you in.",
                "Напишите здесь марку и модель машины, что нужно сделать и удобные "
                "день и время — я вас запишу.",
                "დაწერეთ აქ მანქანის მარკა და მოდელი, რა არის გასაკეთებელი და "
                "თქვენთვის მოსახერხებელი დღე და დრო — ჩაგწერთ.",
            ),
        ),
        ready_faq(
            "repair_cost",
            (
                "How much will the repair cost?",
                "Сколько будет стоить ремонт?",
                "რა ეღირება შეკეთება?",
            ),
            (
                "I can tell you the prices from our price list. The exact cost of a "
                "repair is known once the car has been checked.",
                "Я назову цены из прайс-листа. Точная стоимость ремонта станет "
                "известна после осмотра машины.",
                "ფასებს ჩვენი ფასების სიიდან გეტყვით. შეკეთების ზუსტი ღირებულება "
                "მანქანის დათვალიერების შემდეგ გახდება ცნობილი.",
            ),
        ),
        open_faq(
            "own_parts",
            (
                "Can I bring my own parts?",
                "Можно ли со своими запчастями?",
                "შეიძლება საკუთარი ნაწილების მოტანა?",
            ),
        ),
        open_faq(
            "warranty",
            (
                "Do you give a warranty on repairs?",
                "Даёте ли вы гарантию на ремонт?",
                "იძლევით გარანტიას შეკეთებაზე?",
            ),
        ),
    ],
    offers=[
        offer(
            "diagnostics",
            Kind.SERVICE,
            (
                "Computer diagnostics",
                "Компьютерная диагностика",
                "კომპიუტერული დიაგნოსტიკა",
            ),
            60,
        ),
        offer(
            "oil_change",
            Kind.SERVICE,
            ("Oil change", "Замена масла", "ზეთის შეცვლა"),
            45,
        ),
        offer(
            "tyre_change",
            Kind.SERVICE,
            ("Tyre change", "Шиномонтаж", "საბურავების შეცვლა"),
            60,
        ),
    ],
)

CAR_RENTAL_AND_TOURS_STARTERS = NicheStarterDefinition(
    niche_key=NicheKey.CAR_RENTAL_AND_TOURS,
    opening=opening((at(9), at(20)), (at(9), at(20))),
    booking=booking(
        1440,
        5,
        720,
        (
            "Please cancel or change your booking at least 24 hours before pick-up.",
            "Пожалуйста, отменяйте или меняйте бронь не позже чем за 24 часа до "
            "получения машины.",
            "გთხოვთ, ჯავშანი გააუქმოთ ან შეცვალოთ მანქანის მიღებამდე მინიმუმ 24 "
            "საათით ადრე.",
        ),
    ),
    resource=resource(
        ("Economy car", "Машина эконом-класса", "ეკონომ კლასის ავტომობილი"), 5, 3
    ),
    tones=text(
        (
            "Friendly and clear, with practical details",
            "Дружелюбно и понятно, с практичными деталями",
            "მეგობრულად და გასაგებად, პრაქტიკული დეტალებით",
        )
    ),
    faq=[
        ready_faq(
            "book_car",
            (
                "How do I rent a car?",
                "Как арендовать машину?",
                "როგორ ვიქირაო მანქანა?",
            ),
            (
                "Write the dates, where you want to pick up the car and how many "
                "people will travel here, and I will check what is free and book it.",
                "Напишите здесь даты, где удобно забрать машину и сколько будет "
                "людей, — я проверю свободные машины и забронирую.",
                "დაწერეთ აქ თარიღები, სად გსურთ მანქანის აყვანა და რამდენი ადამიანი "
                "იმგზავრებს — შევამოწმებ თავისუფალ მანქანებს და დაგიჯავშნით.",
            ),
        ),
        CHANGE_RESERVATION,
        open_faq(
            "documents",
            (
                "What documents do I need to rent a car?",
                "Какие документы нужны для аренды?",
                "რა დოკუმენტებია საჭირო მანქანის ქირაობისთვის?",
            ),
        ),
        open_faq(
            "rental_deposit",
            (
                "Is there a deposit?",
                "Нужен ли залог?",
                "საჭიროა დეპოზიტი?",
            ),
        ),
    ],
    offers=[
        offer(
            "economy_car",
            Kind.VEHICLE,
            (
                "Economy car per day",
                "Машина эконом-класса на день",
                "ეკონომ კლასის ავტომობილი დღეში",
            ),
        ),
        offer("suv", Kind.VEHICLE, ("SUV per day", "Внедорожник на день", "ჯიპი დღეში")),
        offer(
            "day_tour",
            Kind.PACKAGE,
            (
                "Day tour with a driver",
                "Однодневный тур с водителем",
                "ერთდღიანი ტური მძღოლით",
            ),
            480,
        ),
    ],
)

HOME_SERVICES_STARTERS = NicheStarterDefinition(
    niche_key=NicheKey.HOME_SERVICES,
    opening=opening((at(9), at(19)), None),
    booking=booking(120, 1, 240, NOTICE_TWELVE_HOURS),
    resource=resource(
        ("Specialist visit", "Выезд мастера", "ხელოსნის გამოძახება"), 1, 2
    ),
    tones=text(
        (
            "Clear, practical and reliable",
            "Чётко, практично и надёжно",
            "მკაფიოდ, პრაქტიკულად და საიმედოდ",
        )
    ),
    faq=[
        ready_faq(
            "book_visit",
            (
                "How do I call a specialist?",
                "Как вызвать мастера?",
                "როგორ გამოვიძახო ხელოსანი?",
            ),
            (
                "Write what needs doing, your address and a convenient day and time "
                "here, and I will book the visit.",
                "Напишите здесь, что нужно сделать, адрес и удобные день и время — я "
                "запишу выезд мастера.",
                "დაწერეთ აქ, რა არის გასაკეთებელი, მისამართი და თქვენთვის "
                "მოსახერხებელი დღე და დრო — ხელოსნის ვიზიტს ჩაგწერთ.",
            ),
        ),
        ready_faq(
            "work_cost",
            (
                "How much will the work cost?",
                "Сколько будет стоить работа?",
                "რა ეღირება სამუშაო?",
            ),
            (
                "I can tell you the prices from our price list. The exact cost is "
                "known once the specialist has seen the job.",
                "Я назову цены из прайс-листа. Точная стоимость станет известна, "
                "когда мастер посмотрит на месте.",
                "ფასებს ჩვენი ფასების სიიდან გეტყვით. ზუსტი ღირებულება ცნობილი "
                "გახდება, როცა ხელოსანი ადგილზე ნახავს.",
            ),
        ),
        open_faq(
            "service_area",
            (
                "Which areas do you cover?",
                "В какие районы вы выезжаете?",
                "რომელ რაიონებში გამოდიხართ?",
            ),
        ),
        open_faq(
            "materials",
            (
                "Do you bring the materials?",
                "Привозите ли вы материалы?",
                "მასალები თქვენ მოგაქვთ?",
            ),
        ),
    ],
    offers=[
        offer(
            "call_out",
            Kind.SERVICE,
            ("Specialist call-out", "Выезд мастера", "ხელოსნის გამოძახება"),
            60,
        ),
        offer(
            "plumbing_repair",
            Kind.SERVICE,
            ("Plumbing repair", "Ремонт сантехники", "სანტექნიკის შეკეთება"),
            60,
        ),
        offer(
            "deep_cleaning",
            Kind.SERVICE,
            (
                "Deep cleaning of an apartment",
                "Генеральная уборка квартиры",
                "ბინის გენერალური დალაგება",
            ),
            240,
        ),
    ],
)
