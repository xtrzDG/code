from app.registries.niches.examples.service_examples import CAR_SERVICE_EXAMPLES
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


def build_car_service_template() -> NicheTemplate:
    """Car services, tire shops and car washes: bays and services (wave B)."""

    return NicheTemplate(
        key=NicheKey.CAR_SERVICE,
        wave=LaunchWave.B,
        names=text(
            en="Car services, tire shops and car washes",
            ru="Автосервисы, шиномонтаж и мойки",
            ka="ავტოსერვისები, ვულკანიზაცია და ავტოსამრეცხაოები",
        ),
        descriptions=text(
            en="Appointments, 'from' prices and what to bring; repair status "
            "comes in the second version.",
            ru="Запись на время, цены «от», что взять с собой; статус ремонта — "
            "во второй версии.",
            ka="ჩაწერა დროზე, ფასები „დან“, რა უნდა წამოიღოთ; რემონტის სტატუსი "
            "— მეორე ვერსიაში.",
        ),
        recommended_plans=[PlanKey.VOICE_AND_CHAT],
        resource_kind=ResourceKind.BAY,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(en="service bay", ru="пост", ka="სარემონტო ბოქსი"),
        knowledge_kinds=[
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                QuestionKey("services_offered"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                text(
                    en="Which services do you offer?",
                    ru="Какие услуги вы оказываете?",
                    ka="რა მომსახურებას გთავაზობთ?",
                ),
                is_required=True,
                choices=[
                    choice(
                        Choice("diagnostics"),
                        "Diagnostics",
                        "Диагностика",
                        "დიაგნოსტიკა",
                    ),
                    choice(Choice("repair"), "Repair", "Ремонт", "რემონტი"),
                    choice(
                        Choice("oil_change"),
                        "Oil change",
                        "Замена масла",
                        "ზეთის შეცვლა",
                    ),
                    choice(
                        Choice("tire_service"),
                        "Tire service",
                        "Шиномонтаж",
                        "ვულკანიზაცია",
                    ),
                    choice(Choice("car_wash"), "Car wash", "Мойка", "სამრეცხაო"),
                    choice(
                        Choice("body_work"),
                        "Body work and paint",
                        "Кузовной ремонт и покраска",
                        "თუნუქის სამუშაოები და შეღებვა",
                    ),
                    choice(
                        Choice("detailing"),
                        "Detailing",
                        "Детейлинг",
                        "დითეილინგი",
                    ),
                ],
            ),
            question(
                QuestionKey("car_brands"),
                Step.OFFER,
                Answer.SHORT_TEXT,
                text(
                    en="Which car brands do you work with?",
                    ru="С какими марками авто вы работаете?",
                    ka="რომელი მარკის მანქანებთან მუშაობთ?",
                ),
            ),
            question(
                QuestionKey("price_note"),
                Step.OFFER,
                Answer.SHORT_TEXT,
                text(
                    en="How should the assistant describe prices?",
                    ru="Как помощник говорит о ценах?",
                    ka="როგორ ისაუბროს ასისტენტმა ფასებზე?",
                ),
                hints=text(
                    en="For example: prices are 'from'; the final price is set "
                    "after diagnostics.",
                    ru="Например: цены «от», точная цена — после диагностики.",
                    ka="მაგალითად: ფასები „დან“, საბოლოო ფასი დიაგნოსტიკის შემდეგ "
                    "დგინდება.",
                ),
            ),
            question(
                QuestionKey("what_to_bring"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
                text(
                    en="What should customers bring?",
                    ru="Что клиенту взять с собой?",
                    ka="რა წამოიღოს კლიენტმა?",
                ),
            ),
            question(
                QuestionKey("waiting_area"),
                Step.FAQ_AND_HANDOFF,
                Answer.YES_NO,
                text(
                    en="Can customers wait on site?",
                    ru="Можно ли подождать на месте?",
                    ka="შეუძლია კლიენტს ადგილზე ლოდინი?",
                ),
            ),
            question(
                QuestionKey("warranty"),
                Step.FAQ_AND_HANDOFF,
                Answer.SHORT_TEXT,
                text(
                    en="Warranty on work",
                    ru="Гарантия на работы",
                    ka="სამუშაოების გარანტია",
                ),
            ),
        ],
        prompt_rules=prompt_rules(
            "Repair prices are 'from' prices: quote them only from the price list "
            "and say that the final price is set after diagnostics.",
            "Book the service bay for the duration of the service from the price list.",
            "Do not diagnose a car over chat or phone; offer a diagnostics "
            "appointment.",
        ),
        example_exchanges=CAR_SERVICE_EXAMPLES,
        default_handoff_rules=handoff_rules(
            en=[
                "Complex repair that needs an estimate",
                "Complaint about completed work",
                "A car broke down on the road and needs towing",
            ],
            ru=[
                "Сложный ремонт, нужна оценка",
                "Жалоба на выполненную работу",
                "Машина сломалась в дороге, нужна эвакуация",
            ],
            ka=[
                "რთული რემონტი, საჭიროა შეფასება",
                "საჩივარი შესრულებულ სამუშაოზე",
                "მანქანა გზაზე გაფუჭდა და ევაკუაცია სჭირდება",
            ],
        ),
        default_forbidden_rules=forbidden_rules(
            en=["Final repair prices before diagnostics"],
            ru=["Окончательная цена ремонта до диагностики"],
            ka=["რემონტის საბოლოო ფასი დიაგნოსტიკამდე"],
        ),
        autotest_kinds=autotest_kinds(),
        integrations=[IntegrationName("Google Calendar")],
    )
