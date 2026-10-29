"""Starter answers of beauty salons, clinics and veterinary clinics."""

from app.registries.niches.starters.starter_parts import (
    CARD_PAYMENT,
    CHANGE_APPOINTMENT,
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

BEAUTY_SALON_STARTERS = NicheStarterDefinition(
    niche_key=NicheKey.BEAUTY_SALON,
    opening=opening((at(10), at(20)), (at(10), at(18))),
    booking=booking(60, 1, 60, NOTICE_THREE_HOURS),
    resource=resource(("Master", "Мастер", "ოსტატი"), 1, 2),
    tones=text(
        (
            "Caring and friendly, short answers",
            "Заботливый и дружелюбный, короткие ответы",
            "მზრუნველი და მეგობრული, მოკლე პასუხები",
        )
    ),
    faq=[
        ready_faq(
            "book_visit",
            (
                "How do I book an appointment?",
                "Как записаться?",
                "როგორ ჩავეწერო?",
            ),
            (
                "Write the service and a convenient day and time here, and I will "
                "book you in.",
                "Напишите здесь услугу и удобные день и время — я вас запишу.",
                "დაწერეთ აქ მომსახურება და თქვენთვის მოსახერხებელი დღე და დრო — "
                "ჩაგწერთ.",
            ),
        ),
        CHANGE_APPOINTMENT,
        open_faq(
            "products",
            (
                "Which brands of products do you use?",
                "Какой косметикой вы работаете?",
                "რომელი ბრენდის საშუალებებს იყენებთ?",
            ),
        ),
        CARD_PAYMENT,
    ],
    offers=[
        offer(
            "haircut",
            Kind.SERVICE,
            ("Women's haircut", "Женская стрижка", "ქალის თმის შეჭრა"),
            60,
        ),
        offer(
            "manicure",
            Kind.SERVICE,
            ("Manicure with gel polish", "Маникюр с гель-лаком", "მანიკური გელ-ლაქით"),
            60,
        ),
        offer(
            "hair_colouring",
            Kind.SERVICE,
            ("Hair colouring", "Окрашивание волос", "თმის შეღებვა"),
            120,
        ),
    ],
)

CLINIC_STARTERS = NicheStarterDefinition(
    niche_key=NicheKey.CLINIC,
    opening=opening((at(9), at(19)), (at(10), at(15))),
    booking=booking(
        30,
        1,
        60,
        (
            "Please let us know at least 24 hours in advance if you cannot come.",
            "Если не сможете прийти, предупредите нас, пожалуйста, хотя бы за 24 часа.",
            "თუ ვერ მოხვალთ, გთხოვთ, გაგვაფრთხილოთ მინიმუმ 24 საათით ადრე.",
        ),
    ),
    resource=resource(("Doctor", "Врач", "ექიმი"), 1, 2),
    tones=text(
        (
            "Calm, polite and precise; no medical advice",
            "Спокойный, вежливый и точный; без медицинских советов",
            "მშვიდი, თავაზიანი და ზუსტი; სამედიცინო რჩევების გარეშე",
        )
    ),
    faq=[
        ready_faq(
            "book_visit",
            (
                "How do I book an appointment with a doctor?",
                "Как записаться к врачу?",
                "როგორ ჩავეწერო ექიმთან?",
            ),
            (
                "Write which doctor or service you need and a convenient day and "
                "time here, and I will book you in.",
                "Напишите здесь, к какому врачу или на какую услугу нужно, и удобные "
                "день и время — я вас запишу.",
                "დაწერეთ აქ, რომელ ექიმთან ან რა მომსახურება გჭირდებათ და თქვენთვის "
                "მოსახერხებელი დღე და დრო — ჩაგწერთ.",
            ),
        ),
        ready_faq(
            "emergency",
            (
                "What should I do in an emergency?",
                "Что делать в экстренной ситуации?",
                "რა გავაკეთო გადაუდებელ შემთხვევაში?",
            ),
            (
                "In an emergency, call the emergency services right away. I can only "
                "help with appointments and questions about our clinic.",
                "В экстренной ситуации сразу звоните в службу экстренной помощи. Я "
                "помогаю только с записью и вопросами о клинике.",
                "გადაუდებელ შემთხვევაში დაუყოვნებლივ დარეკეთ სასწრაფო სამსახურში. მე "
                "მხოლოდ ჩაწერასა და კლინიკის შესახებ კითხვებში შემიძლია დაგეხმაროთ.",
            ),
        ),
        open_faq(
            "insurance",
            (
                "Do you accept health insurance?",
                "Работаете ли вы со страховкой?",
                "მუშაობთ სადაზღვევო კომპანიებთან?",
            ),
        ),
        open_faq(
            "test_results",
            (
                "How do I get my test results?",
                "Как получить результаты анализов?",
                "როგორ მივიღო ანალიზის პასუხები?",
            ),
        ),
    ],
    offers=[
        offer(
            "consultation",
            Kind.SERVICE,
            ("Doctor's consultation", "Консультация врача", "ექიმის კონსულტაცია"),
            30,
        ),
        offer(
            "follow_up_visit",
            Kind.SERVICE,
            ("Follow-up visit", "Повторный приём", "განმეორებითი ვიზიტი"),
            20,
        ),
        offer(
            "blood_test",
            Kind.SERVICE,
            ("Blood test", "Анализ крови", "სისხლის ანალიზი"),
            15,
        ),
    ],
)

VETERINARY_STARTERS = NicheStarterDefinition(
    niche_key=NicheKey.VETERINARY,
    opening=opening((at(9), at(20)), (at(10), at(17))),
    booking=booking(30, 1, 60, NOTICE_THREE_HOURS),
    resource=resource(("Vet", "Ветеринар", "ვეტერინარი"), 1, 1),
    tones=text(
        (
            "Kind and calm, caring about the pet and its owner",
            "Добрый и спокойный, с заботой о питомце и хозяине",
            "კეთილი და მშვიდი, ზრუნვით ცხოველსა და პატრონზე",
        )
    ),
    faq=[
        ready_faq(
            "book_visit",
            (
                "How do I book a visit for my pet?",
                "Как записать питомца на приём?",
                "როგორ ჩავწერო ცხოველი ვიზიტზე?",
            ),
            (
                "Write the kind of pet, what it needs and a convenient day and time "
                "here, and I will book the visit.",
                "Напишите здесь, какой у вас питомец, что ему нужно и удобные день и "
                "время — я запишу на приём.",
                "დაწერეთ აქ, რა ცხოველი გყავთ, რა სჭირდება და თქვენთვის მოსახერხებელი "
                "დღე და დრო — ვიზიტზე ჩაგწერთ.",
            ),
        ),
        ready_faq(
            "emergency",
            (
                "My pet is badly hurt or very ill. What should I do?",
                "Питомец сильно травмирован или тяжело болен. Что делать?",
                "ჩემი ცხოველი მძიმედ არის დაშავებული ან ავად. რა გავაკეთო?",
            ),
            (
                "Call the clinic right away or go to the nearest emergency vet. I "
                "will also pass your message to our team now.",
                "Сразу позвоните в клинику или поезжайте в ближайшую экстренную "
                "ветклинику. Я тоже прямо сейчас передам ваше сообщение команде.",
                "დაუყოვნებლივ დარეკეთ კლინიკაში ან წადით უახლოეს სასწრაფო "
                "ვეტკლინიკაში. თქვენს შეტყობინებას ახლავე გადავცემ ჩვენს გუნდს.",
            ),
        ),
        open_faq(
            "house_calls",
            (
                "Do you make house calls?",
                "Выезжаете ли вы на дом?",
                "გამოდიხართ სახლში?",
            ),
        ),
        open_faq(
            "grooming",
            (
                "Do you do grooming?",
                "Есть ли у вас груминг?",
                "გაქვთ გრუმინგი?",
            ),
        ),
    ],
    offers=[
        offer("checkup", Kind.SERVICE, ("Check-up", "Осмотр", "გასინჯვა"), 30),
        offer(
            "vaccination",
            Kind.SERVICE,
            ("Vaccination", "Вакцинация", "ვაქცინაცია"),
            20,
        ),
        offer(
            "grooming_session",
            Kind.SERVICE,
            ("Grooming", "Груминг", "გრუმინგი"),
            90,
        ),
    ],
)
