from app.registries.niches.template_parts import (
    autotest_kinds,
    choice,
    forbidden_rules,
    handoff_rules,
    prompt_rules,
    question,
    text,
)
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import LaunchWave, NicheKey
from app.schemas.constants.niches import ProfileWizardStep as Step
from app.schemas.constants.niches import QuestionAnswerType as Answer
from app.schemas.dto.niches import NicheTemplate
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey as Choice,
)
from app.schemas.typings.profiles.constrained_strings import QuestionKey


def build_event_venue_template() -> NicheTemplate:
    """Banquet halls, wedding venues and catering: requests to managers (wave B)."""

    return NicheTemplate(
        key=NicheKey.EVENT_VENUE,
        wave=LaunchWave.B,
        names=text(
            en="Banquet halls, wedding venues and catering",
            ru="Банкетные залы, свадебные площадки и кейтеринг",
            ka="საბანკეტო დარბაზები, საქორწილო სივრცეები და კეიტერინგი",
        ),
        descriptions=text(
            en="Requests with the date, guests, budget and menu go straight to a "
            "manager; free dates.",
            ru="Заявка: дата, число гостей, бюджет, меню — сразу менеджеру; "
            "свободные даты.",
            ka="მოთხოვნა: თარიღი, სტუმრების რაოდენობა, ბიუჯეტი, მენიუ — "
            "პირდაპირ მენეჯერს; თავისუფალი თარიღები.",
        ),
        recommended_plans=[PlanKey.CHAT, PlanKey.VOICE_AND_CHAT],
        resource_kind=ResourceKind.ROOM,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(en="hall", ru="зал", ka="დარბაზი"),
        knowledge_kinds=[
            KnowledgeItemKind.PACKAGE,
            KnowledgeItemKind.MENU_ITEM,
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                QuestionKey("event_types"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                text(
                    en="Which events do you host?",
                    ru="Какие мероприятия вы проводите?",
                    ka="რა ღონისძიებებს მასპინძლობთ?",
                ),
                is_required=True,
                choices=[
                    choice(Choice("wedding"), "Weddings", "Свадьбы", "ქორწილები"),
                    choice(
                        Choice("birthday"),
                        "Birthdays",
                        "Дни рождения",
                        "დაბადების დღეები",
                    ),
                    choice(
                        Choice("corporate"),
                        "Corporate events",
                        "Корпоративы",
                        "კორპორატივები",
                    ),
                    choice(
                        Choice("conference"),
                        "Conferences",
                        "Конференции",
                        "კონფერენციები",
                    ),
                    choice(
                        Choice("catering_only"),
                        "Catering only",
                        "Только кейтеринг",
                        "მხოლოდ კეიტერინგი",
                    ),
                ],
            ),
            question(
                QuestionKey("max_guests"),
                Step.BOOKING_RULES,
                Answer.NUMBER,
                text(
                    en="Maximum number of guests",
                    ru="Максимум гостей",
                    ka="სტუმრების მაქსიმალური რაოდენობა",
                ),
                is_required=True,
            ),
            question(
                QuestionKey("catering"),
                Step.OFFER,
                Answer.SINGLE_CHOICE,
                text(en="Food", ru="Питание", ka="კვება"),
                choices=[
                    choice(
                        Choice("own_kitchen"),
                        "Our own kitchen",
                        "Своя кухня",
                        "საკუთარი სამზარეულო",
                    ),
                    choice(
                        Choice("external_allowed"),
                        "Outside catering allowed",
                        "Можно свой кейтеринг",
                        "გარე კეიტერინგი დაშვებულია",
                    ),
                    choice(
                        Choice("no_food"),
                        "No food service",
                        "Без питания",
                        "კვების გარეშე",
                    ),
                ],
            ),
            question(
                QuestionKey("own_drinks"),
                Step.OFFER,
                Answer.YES_NO,
                text(
                    en="May guests bring their own drinks?",
                    ru="Можно ли приносить свои напитки?",
                    ka="შეუძლიათ სტუმრებს საკუთარი სასმელის მოტანა?",
                ),
            ),
            question(
                QuestionKey("decor_and_equipment"),
                Step.OFFER,
                Answer.LONG_TEXT,
                text(
                    en="Decor, sound and equipment",
                    ru="Декор, звук и оборудование",
                    ka="დეკორი, ხმა და აღჭურვილობა",
                ),
            ),
            question(
                QuestionKey("lead_fields"),
                Step.FAQ_AND_HANDOFF,
                Answer.MULTIPLE_CHOICE,
                text(
                    en="What should the assistant collect for a manager?",
                    ru="Что помощник собирает для менеджера?",
                    ka="რა შეაგროვოს ასისტენტმა მენეჯერისთვის?",
                ),
                choices=[
                    choice(
                        Choice("event_date"),
                        "Event date",
                        "Дата мероприятия",
                        "ღონისძიების თარიღი",
                    ),
                    choice(
                        Choice("guest_count"),
                        "Number of guests",
                        "Число гостей",
                        "სტუმრების რაოდენობა",
                    ),
                    choice(Choice("budget"), "Budget", "Бюджет", "ბიუჯეტი"),
                    choice(
                        Choice("menu_wishes"),
                        "Menu wishes",
                        "Пожелания по меню",
                        "სურვილები მენიუზე",
                    ),
                    choice(
                        Choice("contact_time"),
                        "Convenient time to call",
                        "Удобное время для звонка",
                        "ზარისთვის მოსახერხებელი დრო",
                    ),
                ],
            ),
        ],
        prompt_rules=prompt_rules(
            "Every event request becomes a lead: collect the date, number of "
            "guests, budget and menu wishes and pass them to a manager.",
            "Name free dates only from check_availability; a manager confirms the "
            "event date.",
            "Quote packages and per-person prices only from the price list.",
        ),
        default_handoff_rules=handoff_rules(
            en=[
                "Every event request once the details are collected",
                "Complaint",
                "Custom menu or decor beyond the packages",
            ],
            ru=[
                "Каждая заявка на мероприятие после сбора данных",
                "Жалоба",
                "Индивидуальное меню или декор вне пакетов",
            ],
            ka=[
                "ყოველი მოთხოვნა ღონისძიებაზე მონაცემების შეგროვების შემდეგ",
                "საჩივარი",
                "ინდივიდუალური მენიუ ან დეკორი პაკეტების მიღმა",
            ],
        ),
        default_forbidden_rules=forbidden_rules(
            en=["Confirming an event date without a manager"],
            ru=["Подтверждение даты мероприятия без менеджера"],
            ka=["ღონისძიების თარიღის დადასტურება მენეჯერის გარეშე"],
        ),
        autotest_kinds=autotest_kinds(),
    )
