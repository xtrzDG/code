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


def build_car_rental_and_tours_template() -> NicheTemplate:
    """Car rental, transfers and tours: fleet, deposit, prepayment (wave B)."""

    return NicheTemplate(
        key=NicheKey.CAR_RENTAL_AND_TOURS,
        wave=LaunchWave.B,
        names=text(
            en="Car rental, transfers and tours",
            ru="Прокат авто, трансферы и туры",
            ka="მანქანების გაქირავება, ტრანსფერები და ტურები",
        ),
        descriptions=text(
            en="Availability and prices for dates, booking with prepayment by "
            "link, tourist questions in their language.",
            ru="Наличие и цены на даты, бронь с предоплатой по ссылке, вопросы "
            "туристов на их языке.",
            ka="ხელმისაწვდომობა და ფასები თარიღებზე, ჯავშანი წინასწარი "
            "გადახდით ბმულით, ტურისტების კითხვები მათ ენაზე.",
        ),
        recommended_plans=[PlanKey.CHAT, PlanKey.VOICE_AND_CHAT],
        resource_kind=ResourceKind.VEHICLE,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(en="car", ru="автомобиль", ka="ავტომობილი"),
        knowledge_kinds=[
            KnowledgeItemKind.VEHICLE,
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.PACKAGE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                QuestionKey("offer_types"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                text(
                    en="What do you offer?",
                    ru="Что вы предлагаете?",
                    ka="რას გთავაზობთ?",
                ),
                is_required=True,
                choices=[
                    choice(
                        Choice("car_rental"),
                        "Car rental",
                        "Прокат авто",
                        "მანქანის გაქირავება",
                    ),
                    choice(
                        Choice("transfers"),
                        "Transfers",
                        "Трансферы",
                        "ტრანსფერები",
                    ),
                    choice(Choice("tours"), "Tours", "Туры", "ტურები"),
                ],
            ),
            question(
                QuestionKey("roadside_phone"),
                Step.CONTACTS_AND_HOURS,
                Answer.PHONE_NUMBER,
                text(
                    en="Roadside assistance phone",
                    ru="Телефон помощи на дороге",
                    ka="გზაზე დახმარების ტელეფონი",
                ),
            ),
            question(
                QuestionKey("fleet"),
                Step.OFFER,
                Answer.LONG_TEXT,
                text(
                    en="Describe your fleet",
                    ru="Опишите автопарк",
                    ka="აღწერეთ ავტოპარკი",
                ),
                hints=text(
                    en="Add each car model with its daily price to the price list.",
                    ru="Каждую модель с ценой за сутки добавьте в прайс.",
                ),
            ),
            question(
                QuestionKey("pickup_options"),
                Step.OFFER,
                Answer.LONG_TEXT,
                text(
                    en="Where can customers pick up and return cars?",
                    ru="Где можно получить и вернуть автомобиль?",
                    ka="სად შეიძლება მანქანის აღება და დაბრუნება?",
                ),
            ),
            question(
                QuestionKey("tour_languages"),
                Step.OFFER,
                Answer.SHORT_TEXT,
                text(
                    en="In which languages do you run tours?",
                    ru="На каких языках вы проводите туры?",
                    ka="რომელ ენებზე ატარებთ ტურებს?",
                ),
            ),
            question(
                QuestionKey("security_deposit"),
                Step.BOOKING_RULES,
                Answer.SHORT_TEXT,
                text(
                    en="Security deposit for a car",
                    ru="Залог за автомобиль",
                    ka="ავტომობილის გირაო",
                ),
                hints=text(
                    en="The amount and how it is returned.",
                    ru="Сумма и как её возвращают.",
                ),
            ),
            question(
                QuestionKey("driver_requirements"),
                Step.BOOKING_RULES,
                Answer.LONG_TEXT,
                text(
                    en="Driver requirements (age, driving experience, documents)",
                    ru="Требования к водителю (возраст, стаж, документы)",
                    ka="მოთხოვნები მძღოლის მიმართ (ასაკი, სტაჟი, დოკუმენტები)",
                ),
            ),
        ],
        prompt_rules=prompt_rules(
            "Check availability for the exact dates before you confirm a car, a "
            "transfer or a tour.",
            "A booking with prepayment is confirmed only after payment by the "
            "payment link from the profile.",
            "State the deposit and driver requirements only as written in the profile.",
        ),
        default_handoff_rules=handoff_rules(
            en=[
                "Accident, breakdown or problem on the road",
                "Complaint",
                "Custom tour or group request",
                "Rental longer than 30 days",
            ],
            ru=[
                "ДТП, поломка или проблема в дороге",
                "Жалоба",
                "Индивидуальный тур или запрос для группы",
                "Аренда дольше 30 дней",
            ],
            ka=[
                "ავარია, გაფუჭება ან პრობლემა გზაზე",
                "საჩივარი",
                "ინდივიდუალური ტური ან ჯგუფის მოთხოვნა",
                "30 დღეზე მეტი ქირაობა",
            ],
        ),
        default_forbidden_rules=forbidden_rules(
            en=["Confirming a car without checking availability"],
            ru=["Подтверждение автомобиля без проверки наличия"],
            ka=["ავტომობილის დადასტურება ხელმისაწვდომობის შემოწმების გარეშე"],
        ),
        autotest_kinds=autotest_kinds(),
    )
