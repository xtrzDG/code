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


def build_home_services_template() -> NicheTemplate:
    """Home services: cleaning, repairs and handymen at the customer (wave C)."""

    return NicheTemplate(
        key=NicheKey.HOME_SERVICES,
        wave=LaunchWave.C,
        names=text(
            en="Home services: cleaning, repairs, handymen",
            ru="Услуги на дому: клининг, ремонт, мастера",
            ka="სახლის მომსახურება: დალაგება, რემონტი, ხელოსნები",
        ),
        descriptions=text(
            en="Estimates from the price list, appointments, the address and "
            "photos of the task.",
            ru="Расчёт по прайсу, запись на время, адрес и фото задачи.",
            ka="გაანგარიშება ფასების მიხედვით, ჩაწერა დროზე, მისამართი და "
            "დავალების ფოტო.",
        ),
        recommended_plans=[PlanKey.CHAT],
        resource_kind=ResourceKind.STAFF,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(en="specialist", ru="мастер", ka="ხელოსანი"),
        knowledge_kinds=[
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                QuestionKey("service_types"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                text(
                    en="Which services do you offer?",
                    ru="Какие услуги вы оказываете?",
                    ka="რა მომსახურებას გთავაზობთ?",
                ),
                is_required=True,
                choices=[
                    choice(Choice("cleaning"), "Cleaning", "Клининг", "დალაგება"),
                    choice(
                        Choice("plumbing"),
                        "Plumbing",
                        "Сантехника",
                        "სანტექნიკა",
                    ),
                    choice(
                        Choice("electrical"),
                        "Electrical work",
                        "Электрика",
                        "ელექტროობა",
                    ),
                    choice(
                        Choice("appliance_repair"),
                        "Appliance repair",
                        "Ремонт техники",
                        "ტექნიკის შეკეთება",
                    ),
                    choice(
                        Choice("renovation"),
                        "Renovation",
                        "Ремонт помещений",
                        "სარემონტო სამუშაოები",
                    ),
                    choice(
                        Choice("handyman"),
                        "Small household jobs",
                        "Мелкий бытовой ремонт",
                        "წვრილმანი საოჯახო სამუშაოები",
                    ),
                ],
            ),
            question(
                QuestionKey("service_area"),
                Step.CONTACTS_AND_HOURS,
                Answer.SHORT_TEXT,
                text(
                    en="Which areas do you serve?",
                    ru="В каких районах вы работаете?",
                    ka="რომელ რაიონებში მუშაობთ?",
                ),
                is_required=True,
            ),
            question(
                QuestionKey("pricing_basis"),
                Step.OFFER,
                Answer.SINGLE_CHOICE,
                text(
                    en="How do you price jobs?",
                    ru="Как вы считаете стоимость?",
                    ka="როგორ ითვლით ღირებულებას?",
                ),
                choices=[
                    choice(
                        Choice("per_hour"),
                        "Per hour",
                        "За час",
                        "საათობრივად",
                    ),
                    choice(
                        Choice("per_square_meter"),
                        "Per square meter",
                        "За квадратный метр",
                        "კვადრატულ მეტრზე",
                    ),
                    choice(
                        Choice("per_job"),
                        "Per job",
                        "За работу",
                        "სამუშაოზე",
                    ),
                    choice(
                        Choice("after_inspection"),
                        "After an inspection",
                        "После осмотра",
                        "დათვალიერების შემდეგ",
                    ),
                ],
            ),
            question(
                QuestionKey("call_out_fee"),
                Step.OFFER,
                Answer.SHORT_TEXT,
                text(
                    en="Call-out fee",
                    ru="Стоимость выезда",
                    ka="გამოძახების საფასური",
                ),
            ),
            question(
                QuestionKey("ask_for_photos"),
                Step.BOOKING_RULES,
                Answer.YES_NO,
                text(
                    en="Should the assistant ask for photos of the task?",
                    ru="Просить ли у клиента фото задачи?",
                    ka="სთხოვოს ასისტენტმა კლიენტს დავალების ფოტო?",
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
                    choice(Choice("address"), "Address", "Адрес", "მისამართი"),
                    choice(
                        Choice("task_description"),
                        "Task description",
                        "Описание задачи",
                        "დავალების აღწერა",
                    ),
                    choice(Choice("photos"), "Photos", "Фото", "ფოტოები"),
                    choice(
                        Choice("preferred_time"),
                        "Preferred time",
                        "Удобное время",
                        "სასურველი დრო",
                    ),
                ],
            ),
        ],
        prompt_rules=prompt_rules(
            "Give estimates only from the price list and say that the specialist "
            "confirms the final price.",
            "Collect the address, a description of the task and a convenient time "
            "before you book a visit.",
            "For emergencies such as a water leak, a gas smell or sparking wiring, "
            "tell the customer to call the local emergency service first and hand "
            "off with high urgency.",
        ),
        default_handoff_rules=handoff_rules(
            en=[
                "Emergency at home (leak, electrical fault)",
                "Large job that needs an inspection",
                "Complaint",
            ],
            ru=[
                "Авария дома (протечка, неисправность электрики)",
                "Большой объём работ, нужен осмотр",
                "Жалоба",
            ],
            ka=[
                "ავარია სახლში (გაჟონვა, ელექტროობის გაუმართაობა)",
                "დიდი მოცულობის სამუშაო, საჭიროა დათვალიერება",
                "საჩივარი",
            ],
        ),
        default_forbidden_rules=forbidden_rules(
            en=["Final prices before an inspection"],
            ru=["Окончательная цена до осмотра"],
            ka=["საბოლოო ფასი დათვალიერებამდე"],
        ),
        autotest_kinds=autotest_kinds(),
    )
