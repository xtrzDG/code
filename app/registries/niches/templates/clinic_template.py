from app.registries.niches.template_parts import (
    autotest_kinds,
    choice,
    forbidden_rules,
    handoff_rules,
    prompt_rules,
    question,
    text,
)
from app.schemas.constants.assistants import AutotestScenarioKind
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


def build_clinic_template() -> NicheTemplate:
    """
    Dental and private clinics (wave B).

    Health data needs a lawyer's review before launch, and the assistant never
    gives medical advice: it books visits and sends emergencies to people.
    """

    return NicheTemplate(
        key=NicheKey.CLINIC,
        wave=LaunchWave.B,
        names=text(
            en="Dental and private clinics",
            ru="Стоматологии и частные клиники",
            ka="სტომატოლოგიები და კერძო კლინიკები",
        ),
        descriptions=text(
            en="Appointments with a doctor, prices, visit preparation and the "
            "address. Never gives medical advice; urgent cases go to a person at "
            "once.",
            ru="Запись к врачу, цены, подготовка к приёму, адрес. Медицинских "
            "советов не даёт, срочное сразу передаёт человеку.",
            ka="ჩაწერა ექიმთან, ფასები, ვიზიტისთვის მომზადება და მისამართი. "
            "სამედიცინო რჩევას არ იძლევა, სასწრაფოს მაშინვე ადამიანს გადასცემს.",
        ),
        recommended_plans=[PlanKey.VOICE_AND_CHAT],
        resource_kind=ResourceKind.STAFF,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(en="doctor", ru="врач", ka="ექიმი"),
        knowledge_kinds=[
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                QuestionKey("specialties"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                text(
                    en="Which specialties do you cover?",
                    ru="Какие направления есть в клинике?",
                    ka="რა მიმართულებებია კლინიკაში?",
                ),
                is_required=True,
                choices=[
                    choice(
                        Choice("dentistry"),
                        "Dentistry",
                        "Стоматология",
                        "სტომატოლოგია",
                    ),
                    choice(
                        Choice("general_practice"),
                        "General practice",
                        "Терапия",
                        "თერაპია",
                    ),
                    choice(
                        Choice("pediatrics"),
                        "Pediatrics",
                        "Педиатрия",
                        "პედიატრია",
                    ),
                    choice(
                        Choice("gynecology"),
                        "Gynecology",
                        "Гинекология",
                        "გინეკოლოგია",
                    ),
                    choice(
                        Choice("dermatology"),
                        "Dermatology",
                        "Дерматология",
                        "დერმატოლოგია",
                    ),
                    choice(
                        Choice("ophthalmology"),
                        "Ophthalmology",
                        "Офтальмология",
                        "ოფთალმოლოგია",
                    ),
                    choice(
                        Choice("diagnostics"),
                        "Diagnostics and tests",
                        "Диагностика и анализы",
                        "დიაგნოსტიკა და ანალიზები",
                    ),
                    choice(Choice("other"), "Other", "Другое", "სხვა"),
                ],
            ),
            question(
                QuestionKey("doctors"),
                Step.OFFER,
                Answer.LONG_TEXT,
                text(
                    en="Doctors and their specialties",
                    ru="Врачи и их специализации",
                    ka="ექიმები და მათი სპეციალიზაციები",
                ),
                hints=text(
                    en="Doctors are added as resources; describe here who treats what.",
                    ru="Врачи добавляются как ресурсы; здесь опишите, кто что лечит.",
                ),
            ),
            question(
                QuestionKey("children_accepted"),
                Step.OFFER,
                Answer.YES_NO,
                text(
                    en="Do you treat children?",
                    ru="Принимаете ли вы детей?",
                    ka="იღებთ ბავშვებს?",
                ),
            ),
            question(
                QuestionKey("insurance"),
                Step.FAQ_AND_HANDOFF,
                Answer.SHORT_TEXT,
                text(
                    en="Which insurance do you accept?",
                    ru="Какие страховки вы принимаете?",
                    ka="რომელ დაზღვევას იღებთ?",
                ),
            ),
            question(
                QuestionKey("visit_preparation"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
                text(
                    en="How should patients prepare for a visit?",
                    ru="Как пациенту подготовиться к приёму?",
                    ka="როგორ მოემზადოს პაციენტი ვიზიტისთვის?",
                ),
                hints=text(
                    en="For example: documents to bring, fasting before tests.",
                    ru="Например: какие документы взять, натощак ли сдавать анализы.",
                ),
            ),
            question(
                QuestionKey("emergency_message"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
                text(
                    en="What should the assistant tell a patient in an emergency?",
                    ru="Что помощник говорит пациенту в экстренном случае?",
                    ka="რა უთხრას ასისტენტმა პაციენტს საგანგებო შემთხვევაში?",
                ),
                is_required=True,
                hints=text(
                    en="The assistant always adds the local emergency number and "
                    "passes the conversation to staff.",
                    ru="Помощник всегда добавляет местный номер экстренной службы "
                    "и передаёт разговор сотруднику.",
                ),
            ),
        ],
        prompt_rules=prompt_rules(
            "Never give medical advice, diagnoses, interpretations of symptoms or "
            "test results, or medication recommendations; you only book visits "
            "and share facts from the profile.",
            "If the patient describes urgent symptoms or an emergency, tell them "
            "to call the local emergency number immediately and hand off with "
            "critical urgency.",
            "Ask only for what a booking needs (name, phone, doctor or service); "
            "do not ask about health details.",
            "Share preparation instructions only as written in the profile.",
        ),
        default_handoff_rules=handoff_rules(
            en=[
                "Urgent symptoms or an emergency",
                "Question about a diagnosis, treatment, medication or test results",
                "Complaint",
                "Request for medical documents",
            ],
            ru=[
                "Срочные симптомы или экстренная ситуация",
                "Вопрос о диагнозе, лечении, лекарствах или результатах анализов",
                "Жалоба",
                "Запрос медицинских документов",
            ],
            ka=[
                "სასწრაფო სიმპტომები ან საგანგებო ვითარება",
                "კითხვა დიაგნოზზე, მკურნალობაზე, მედიკამენტებზე ან ანალიზების "
                "შედეგებზე",
                "საჩივარი",
                "სამედიცინო დოკუმენტების მოთხოვნა",
            ],
        ),
        default_forbidden_rules=forbidden_rules(
            en=[
                "Medical advice, diagnoses or medication recommendations",
                "Asking about health details beyond what a booking needs",
            ],
            ru=[
                "Медицинские советы, диагнозы и рекомендации лекарств",
                "Расспросы о здоровье сверх нужного для записи",
            ],
            ka=[
                "სამედიცინო რჩევები, დიაგნოზები და მედიკამენტების რეკომენდაციები",
                "ჯანმრთელობის შესახებ კითხვები იმაზე მეტად, რაც ჩაწერისთვისაა საჭირო",
            ],
        ),
        autotest_kinds=autotest_kinds(AutotestScenarioKind.EMERGENCY),
        integrations=[IntegrationName("Google Calendar")],
        requires_legal_review=True,
    )
