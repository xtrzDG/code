"""Starter answers of real estate agencies and schools and courses."""

from app.registries.niches.starters.starter_parts import (
    CHANGE_APPOINTMENT,
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

REAL_ESTATE_STARTERS = NicheStarterDefinition(
    niche_key=NicheKey.REAL_ESTATE,
    opening=opening((at(10), at(19)), None),
    booking=booking(
        60,
        4,
        240,
        (
            "Please let us know at least 3 hours in advance if you cannot come to "
            "the viewing.",
            "Если не сможете прийти на показ, предупредите нас, пожалуйста, хотя бы "
            "за 3 часа.",
            "თუ ჩვენებაზე ვერ მოხვალთ, გთხოვთ, გაგვაფრთხილოთ მინიმუმ 3 საათით ადრე.",
        ),
    ),
    resource=resource(
        ("Viewing with an agent", "Показ с агентом", "ჩვენება აგენტთან ერთად"), 4, 1
    ),
    tones=text(
        (
            "Professional and trustworthy, clear answers",
            "Профессиональный и надёжный, понятные ответы",
            "პროფესიონალური და სანდო, გასაგები პასუხები",
        )
    ),
    faq=[
        ready_faq(
            "book_viewing",
            (
                "How do I arrange a viewing?",
                "Как договориться о показе?",
                "როგორ შევთანხმდე ჩვენებაზე?",
            ),
            (
                "Write which property interests you and a convenient day and time "
                "here, and I will book a viewing with an agent.",
                "Напишите здесь, какой объект вас интересует, и удобные день и время "
                "— я запишу на показ с агентом.",
                "დაწერეთ აქ, რომელი ობიექტი გაინტერესებთ და თქვენთვის მოსახერხებელი "
                "დღე და დრო — აგენტთან ჩვენებაზე ჩაგწერთ.",
            ),
        ),
        ready_faq(
            "list_property",
            (
                "I want to sell or rent out my property.",
                "Хочу продать или сдать свою недвижимость.",
                "მინდა ჩემი უძრავი ქონების გაყიდვა ან გაქირავება.",
            ),
            (
                "Write the address, the type of property and your phone number here, "
                "and our agent will contact you.",
                "Напишите здесь адрес, тип недвижимости и свой телефон — с вами "
                "свяжется наш агент.",
                "დაწერეთ აქ მისამართი, ქონების ტიპი და თქვენი ტელეფონის ნომერი — "
                "ჩვენი აგენტი დაგიკავშირდებათ.",
            ),
        ),
        open_faq(
            "commission",
            (
                "What is your commission?",
                "Какая у вас комиссия?",
                "რა არის თქვენი საკომისიო?",
            ),
        ),
        open_faq(
            "mortgage",
            (
                "Do you help with a mortgage?",
                "Помогаете ли вы с ипотекой?",
                "გვეხმარებით იპოთეკაში?",
            ),
        ),
    ],
    offers=[
        offer(
            "two_room_flat",
            Kind.PRODUCT,
            (
                "Two-room apartment in the centre",
                "Двухкомнатная квартира в центре",
                "ოროთახიანი ბინა ცენტრში",
            ),
        ),
        offer(
            "family_house",
            Kind.PRODUCT,
            ("Family house with a garden", "Дом для семьи с садом", "საოჯახო სახლი ბაღით"),
        ),
        offer(
            "office_space",
            Kind.PRODUCT,
            ("Office space for rent", "Офис в аренду", "საოფისე ფართი ქირით"),
        ),
    ],
)

EDUCATION_STARTERS = NicheStarterDefinition(
    niche_key=NicheKey.EDUCATION,
    opening=opening((at(10), at(20)), (at(10), at(16))),
    booking=booking(60, 1, 120, NOTICE_TWELVE_HOURS),
    resource=resource(
        (
            "Lesson with a teacher",
            "Занятие с преподавателем",
            "გაკვეთილი მასწავლებელთან",
        ),
        1,
        2,
    ),
    tones=text(
        (
            "Friendly and patient, clear answers",
            "Дружелюбный и терпеливый, понятные ответы",
            "მეგობრული და მომთმენი, გასაგები პასუხები",
        )
    ),
    faq=[
        ready_faq(
            "book_lesson",
            (
                "How do I book a lesson?",
                "Как записаться на занятие?",
                "როგორ ჩავეწერო გაკვეთილზე?",
            ),
            (
                "Write the subject and a convenient day and time here, and I will book "
                "the lesson.",
                "Напишите здесь предмет и удобные день и время — я запишу на занятие.",
                "დაწერეთ აქ საგანი და თქვენთვის მოსახერხებელი დღე და დრო — "
                "გაკვეთილზე ჩაგწერთ.",
            ),
        ),
        CHANGE_APPOINTMENT,
        open_faq(
            "level_test",
            (
                "Is there a level test before the course?",
                "Есть ли тест на уровень перед курсом?",
                "არის დონის ტესტი კურსის დაწყებამდე?",
            ),
        ),
        open_faq(
            "online_lessons",
            (
                "Can I study online?",
                "Можно ли заниматься онлайн?",
                "შეიძლება ონლაინ სწავლა?",
            ),
        ),
    ],
    offers=[
        offer(
            "trial_lesson",
            Kind.SERVICE,
            ("Trial lesson", "Пробное занятие", "საცდელი გაკვეთილი"),
            45,
        ),
        offer(
            "individual_lesson",
            Kind.SERVICE,
            ("Individual lesson", "Индивидуальное занятие", "ინდივიდუალური გაკვეთილი"),
            60,
        ),
        offer(
            "monthly_course",
            Kind.PACKAGE,
            (
                "Monthly group course",
                "Групповой курс на месяц",
                "ერთთვიანი ჯგუფური კურსი",
            ),
        ),
    ],
)
