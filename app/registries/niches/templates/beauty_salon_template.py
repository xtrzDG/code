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
    FactKey,
    QuestionKey,
)
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey as Choice,
)


def build_beauty_salon_template() -> NicheTemplate:
    """Beauty salons, barbershops and spas: appointments with masters (wave A)."""

    return NicheTemplate(
        key=NicheKey.BEAUTY_SALON,
        wave=LaunchWave.A,
        names=text(
            en="Beauty salons, barbershops and spas",
            ru="Салоны красоты, барбершопы и СПА",
            ka="სილამაზის სალონები, ბარბერშოპები და სპა",
        ),
        descriptions=text(
            en="Appointments with a master, rescheduling, service prices and "
            "reminders that reduce no-shows.",
            ru="Запись к мастеру, перенос, цены услуг, напоминания (меньше неявок).",
            ka="ჩაწერა ოსტატთან, გადატანა, მომსახურების ფასები და შეხსენებები "
            "(ნაკლები გაცდენა).",
        ),
        recommended_plans=[PlanKey.CHAT],
        resource_kind=ResourceKind.STAFF,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(en="master", ru="мастер", ka="ოსტატი"),
        knowledge_kinds=[
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.PACKAGE,
            KnowledgeItemKind.PRODUCT,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                QuestionKey("service_categories"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                text(
                    en="Which services do you offer?",
                    ru="Какие услуги вы оказываете?",
                    ka="რა მომსახურებას გთავაზობთ?",
                ),
                is_required=True,
                choices=[
                    choice(Choice("hair"), "Hair", "Волосы", "თმა"),
                    choice(Choice("nails"), "Nails", "Ногти", "ფრჩხილები"),
                    choice(Choice("makeup"), "Makeup", "Макияж", "მაკიაჟი"),
                    choice(
                        Choice("brows_lashes"),
                        "Brows and lashes",
                        "Брови и ресницы",
                        "წარბები და წამწამები",
                    ),
                    choice(
                        Choice("cosmetology"),
                        "Cosmetology",
                        "Косметология",
                        "კოსმეტოლოგია",
                    ),
                    choice(Choice("massage"), "Massage", "Массаж", "მასაჟი"),
                    choice(Choice("barber"), "Barbering", "Барбер", "ბარბერი"),
                    choice(Choice("spa"), "Spa", "СПА", "სპა"),
                ],
            ),
            question(
                QuestionKey("masters_and_services"),
                Step.OFFER,
                Answer.LONG_TEXT,
                text(
                    en="Which master does which services?",
                    ru="Какие услуги делает каждый мастер?",
                    ka="რომელ მომსახურებას ასრულებს თითოეული ოსტატი?",
                ),
                hints=text(
                    en="Masters are added as resources; describe here who does "
                    "what, for example 'Nino: manicure, pedicure'.",
                    ru="Мастера добавляются как ресурсы; здесь опишите, кто что "
                    "делает, например «Нино: маникюр, педикюр».",
                ),
            ),
            question(
                QuestionKey("product_brands"),
                Step.OFFER,
                Answer.SHORT_TEXT,
                text(
                    en="Brands of products you use",
                    ru="Бренды материалов и косметики",
                    ka="გამოყენებული პროდუქციის ბრენდები",
                ),
            ),
            question(
                QuestionKey("break_between_appointments"),
                Step.BOOKING_RULES,
                Answer.NUMBER,
                text(
                    en="Break between appointments, in minutes",
                    ru="Перерыв между записями, в минутах",
                    ka="შესვენება ჩაწერებს შორის, წუთებში",
                ),
                fact_key=FactKey("appointment_break_minutes"),
            ),
            question(
                QuestionKey("client_chooses_master"),
                Step.BOOKING_RULES,
                Answer.YES_NO,
                text(
                    en="Can clients choose a specific master?",
                    ru="Может ли клиент выбрать мастера?",
                    ka="შეუძლია კლიენტს ოსტატის არჩევა?",
                ),
            ),
            question(
                QuestionKey("late_arrival_policy"),
                Step.BOOKING_RULES,
                Answer.LONG_TEXT,
                text(
                    en="What happens if a client is late?",
                    ru="Что делать, если клиент опаздывает?",
                    ka="რა ხდება, თუ კლიენტი აგვიანებს?",
                ),
            ),
        ],
        prompt_rules=prompt_rules(
            "Every service has a duration in the price list: book a slot long "
            "enough for the service with a master who does it.",
            "If the client names a master, book only with that master; otherwise "
            "offer the earliest free master.",
            "Do not judge skin, hair or health conditions; suggest a consultation "
            "with a master instead.",
        ),
        default_handoff_rules=handoff_rules(
            en=[
                "Complaint about the result of a service",
                "Allergic reaction or skin problem after a procedure",
                "Request for a master or a service that is not in the list",
            ],
            ru=[
                "Жалоба на результат услуги",
                "Аллергическая реакция или проблема с кожей после процедуры",
                "Просьба о мастере или услуге, которых нет в списке",
            ],
            ka=[
                "საჩივარი მომსახურების შედეგზე",
                "ალერგიული რეაქცია ან კანის პრობლემა პროცედურის შემდეგ",
                "თხოვნა ოსტატზე ან მომსახურებაზე, რომელიც სიაში არ არის",
            ],
        ),
        default_forbidden_rules=forbidden_rules(
            en=["Advice on medical skin or health conditions"],
            ru=["Советы по медицинским проблемам кожи и здоровья"],
            ka=["რჩევები კანისა და ჯანმრთელობის სამედიცინო პრობლემებზე"],
        ),
        autotest_kinds=autotest_kinds(),
        integrations=[
            IntegrationName("Google Calendar"),
            IntegrationName("Cal.com"),
        ],
    )
