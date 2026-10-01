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
from app.schemas.typings.niches.strings import IntegrationName
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey as Choice,
)
from app.schemas.typings.profiles.constrained_strings import QuestionKey


def build_hotel_template() -> NicheTemplate:
    """Hotels, guest houses and hostels: rooms booked by nights (wave A)."""

    return NicheTemplate(
        key=NicheKey.HOTEL,
        wave=LaunchWave.A,
        names=text(
            en="Hotels, guest houses and hostels",
            ru="Отели, гостевые дома и хостелы",
            ka="სასტუმროები, საოჯახო სასტუმროები და ჰოსტელები",
        ),
        descriptions=text(
            en="Free rooms and prices for dates, direct booking without platform "
            "commission, transfer, early check-in and guest questions around the "
            "clock in many languages.",
            ru="Свободные номера и цены на даты, прямая бронь без комиссии "
            "агрегаторов, трансфер, ранний заезд, вопросы гостей круглосуточно на "
            "многих языках.",
            ka="თავისუფალი ოთახები და ფასები თარიღებზე, პირდაპირი ჯავშანი "
            "აგრეგატორების საკომისიოს გარეშე, ტრანსფერი, ადრეული შესახლება და "
            "სტუმრების კითხვები 24/7 მრავალ ენაზე.",
        ),
        recommended_plans=[PlanKey.VOICE_AND_CHAT, PlanKey.PLUS],
        resource_kind=ResourceKind.ROOM,
        booking_unit=BookingUnit.NIGHT,
        resource_nouns=text(en="room", ru="номер", ka="ოთახი"),
        knowledge_kinds=[
            KnowledgeItemKind.ROOM_TYPE,
            KnowledgeItemKind.PACKAGE,
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                QuestionKey("property_type"),
                Step.NICHE_AND_LANGUAGES,
                Answer.SINGLE_CHOICE,
                text(
                    en="What kind of property is it?",
                    ru="Какой у вас тип размещения?",
                    ka="რა ტიპის განთავსებაა?",
                ),
                is_required=True,
                choices=[
                    choice(Choice("hotel"), "Hotel", "Отель", "სასტუმრო"),
                    choice(
                        Choice("guest_house"),
                        "Guest house",
                        "Гостевой дом",
                        "საოჯახო სასტუმრო",
                    ),
                    choice(Choice("hostel"), "Hostel", "Хостел", "ჰოსტელი"),
                    choice(
                        Choice("apart_hotel"),
                        "Apart-hotel",
                        "Апарт-отель",
                        "აპარტ-სასტუმრო",
                    ),
                ],
            ),
            question(
                QuestionKey("check_in_time"),
                Step.BOOKING_RULES,
                Answer.SHORT_TEXT,
                text(en="Check-in time", ru="Время заезда", ka="შესახლების დრო"),
                is_required=True,
                hints=text(
                    en="For example: from 14:00",
                    ru="Например: с 14:00",
                    ka="მაგალითად: 14:00-დან",
                ),
            ),
            question(
                QuestionKey("check_out_time"),
                Step.BOOKING_RULES,
                Answer.SHORT_TEXT,
                text(en="Check-out time", ru="Время выезда", ka="გამოსახლების დრო"),
                is_required=True,
                hints=text(
                    en="For example: until 12:00",
                    ru="Например: до 12:00",
                    ka="მაგალითად: 12:00-მდე",
                ),
            ),
            question(
                QuestionKey("early_check_in"),
                Step.BOOKING_RULES,
                Answer.LONG_TEXT,
                text(
                    en="Early check-in and late check-out rules",
                    ru="Правила раннего заезда и позднего выезда",
                    ka="ადრეული შესახლებისა და გვიანი გამოსახლების წესები",
                ),
            ),
            question(
                QuestionKey("seasonal_prices"),
                Step.OFFER,
                Answer.LONG_TEXT,
                text(
                    en="How do prices change by season?",
                    ru="Как меняются цены по сезонам?",
                    ka="როგორ იცვლება ფასები სეზონების მიხედვით?",
                ),
                hints=text(
                    en="Room prices go into the price list (use the attribute "
                    "'season'); describe the season dates and rules here.",
                    ru="Цены номеров — в прайсе (атрибут «season»); здесь опишите "
                    "даты сезонов и правила.",
                ),
            ),
            question(
                QuestionKey("breakfast"),
                Step.OFFER,
                Answer.SINGLE_CHOICE,
                text(en="Breakfast", ru="Завтрак", ka="საუზმე"),
                choices=[
                    choice(Choice("none"), "Not available", "Нет", "არ არის"),
                    choice(
                        Choice("included"),
                        "Included in the price",
                        "Включён в цену",
                        "ფასში შედის",
                    ),
                    choice(
                        Choice("extra_charge"),
                        "For an extra charge",
                        "За доплату",
                        "დამატებითი საფასურით",
                    ),
                ],
            ),
            question(
                QuestionKey("transfer"),
                Step.OFFER,
                Answer.SINGLE_CHOICE,
                text(
                    en="Airport or station transfer",
                    ru="Трансфер из аэропорта или с вокзала",
                    ka="ტრანსფერი აეროპორტიდან ან სადგურიდან",
                ),
                choices=[
                    choice(Choice("none"), "Not available", "Нет", "არ არის"),
                    choice(
                        Choice("paid"),
                        "On request, paid",
                        "По запросу, платно",
                        "მოთხოვნით, ფასიანი",
                    ),
                    choice(Choice("free"), "Free", "Бесплатно", "უფასო"),
                ],
            ),
            question(
                QuestionKey("pets_allowed"),
                Step.FAQ_AND_HANDOFF,
                Answer.YES_NO,
                text(
                    en="Are pets allowed?",
                    ru="Можно ли с животными?",
                    ka="შეიძლება შინაური ცხოველებით?",
                ),
            ),
            question(
                QuestionKey("booking_system"),
                Step.CHANNELS,
                Answer.SINGLE_CHOICE,
                text(
                    en="Which booking system (PMS) do you use?",
                    ru="Какой системой бронирования (PMS) вы пользуетесь?",
                    ka="რომელ დაჯავშნის სისტემას (PMS) იყენებთ?",
                ),
                hints=text(
                    en="Add the direct booking link in the links below.",
                    ru="Ссылку на прямую бронь добавьте в ссылки ниже.",
                ),
                choices=[
                    choice(Choice("none"), "None", "Никакой", "არცერთს"),
                    choice(Choice("cloudbeds"), "Cloudbeds", "Cloudbeds"),
                    choice(Choice("mews"), "Mews", "Mews"),
                    choice(Choice("hotelrunner"), "HotelRunner", "HotelRunner"),
                    choice(Choice("other"), "Other", "Другая", "სხვა"),
                ],
            ),
        ],
        prompt_rules=prompt_rules(
            "Rooms are booked by nights: always confirm the check-in date, the "
            "number of nights and the number of guests.",
            "Quote room prices only from the price list and only for the season "
            "that matches the dates; if the season is unclear, say the price "
            "depends on the dates and check get_price.",
            "Offer the direct booking link or a booking through you; never "
            "recommend booking through other platforms.",
            "Guests also write at night: answer arrival questions yourself, but "
            "pass emergencies and complaints to staff right away.",
        ),
        default_handoff_rules=handoff_rules(
            en=[
                "Complaint during the stay",
                "Group booking of more than 5 rooms",
                "Request for a special price or a long stay",
                "A guest cannot get in or has an emergency",
            ],
            ru=[
                "Жалоба во время проживания",
                "Групповая бронь больше 5 номеров",
                "Просьба об особой цене или долгом проживании",
                "Гость не может попасть внутрь или у него экстренная ситуация",
            ],
            ka=[
                "საჩივარი ცხოვრების დროს",
                "ჯგუფური ჯავშანი 5-ზე მეტ ოთახზე",
                "განსაკუთრებული ფასის ან ხანგრძლივი ცხოვრების თხოვნა",
                "სტუმარი ვერ შედის შიგნით ან საგანგებო ვითარებაშია",
            ],
        ),
        default_forbidden_rules=forbidden_rules(
            en=["Confirming a room without checking availability"],
            ru=["Подтверждение номера без проверки наличия"],
            ka=["ოთახის დადასტურება ხელმისაწვდომობის შემოწმების გარეშე"],
        ),
        autotest_kinds=autotest_kinds(),
        integrations=[
            IntegrationName("Cloudbeds"),
            IntegrationName("Mews"),
            IntegrationName("HotelRunner"),
        ],
    )
