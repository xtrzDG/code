from app.registries.niches.examples.care_examples import VETERINARY_EXAMPLES
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
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey as Choice,
)
from app.schemas.typings.profiles.constrained_strings import QuestionKey


def build_veterinary_template() -> NicheTemplate:
    """
    Veterinary clinics and grooming (wave C).

    The assistant never gives veterinary advice; an animal in danger goes to a
    person at once.
    """

    return NicheTemplate(
        key=NicheKey.VETERINARY,
        wave=LaunchWave.C,
        names=text(
            en="Veterinary clinics and grooming",
            ru="Ветклиники и груминг",
            ka="ვეტკლინიკები და გრუმინგი",
        ),
        descriptions=text(
            en="Appointments and prices; urgent cases go to a vet at once.",
            ru="Запись, цены, срочное — сразу врачу.",
            ka="ჩაწერა და ფასები; სასწრაფო შემთხვევები — მაშინვე ექიმს.",
        ),
        recommended_plans=[PlanKey.VOICE_AND_CHAT],
        resource_kind=ResourceKind.STAFF,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(
            en="vet or groomer",
            ru="ветеринар или грумер",
            ka="ვეტერინარი ან გრუმერი",
        ),
        knowledge_kinds=[
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.PRODUCT,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                QuestionKey("animals_treated"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                text(
                    en="Which animals do you treat?",
                    ru="Каких животных вы лечите?",
                    ka="რომელ ცხოველებს მკურნალობთ?",
                ),
                is_required=True,
                choices=[
                    choice(Choice("dogs"), "Dogs", "Собаки", "ძაღლები"),
                    choice(Choice("cats"), "Cats", "Кошки", "კატები"),
                    choice(Choice("birds"), "Birds", "Птицы", "ფრინველები"),
                    choice(
                        Choice("rodents"),
                        "Rodents and rabbits",
                        "Грызуны и кролики",
                        "მღრღნელები და კურდღლები",
                    ),
                    choice(
                        Choice("exotic"),
                        "Exotic animals",
                        "Экзотические животные",
                        "ეგზოტიკური ცხოველები",
                    ),
                ],
            ),
            question(
                QuestionKey("services_offered"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                text(en="Services", ru="Услуги", ka="მომსახურება"),
                choices=[
                    choice(
                        Choice("treatment"),
                        "Treatment",
                        "Лечение",
                        "მკურნალობა",
                    ),
                    choice(
                        Choice("vaccination"),
                        "Vaccination",
                        "Вакцинация",
                        "ვაქცინაცია",
                    ),
                    choice(Choice("surgery"), "Surgery", "Хирургия", "ქირურგია"),
                    choice(Choice("grooming"), "Grooming", "Груминг", "გრუმინგი"),
                    choice(
                        Choice("pet_hotel"),
                        "Pet hotel",
                        "Зоогостиница",
                        "ცხოველების სასტუმრო",
                    ),
                ],
            ),
            question(
                QuestionKey("emergency_hours"),
                Step.CONTACTS_AND_HOURS,
                Answer.LONG_TEXT,
                text(
                    en="When and how do you take emergencies?",
                    ru="Когда и как вы принимаете экстренные случаи?",
                    ka="როდის და როგორ იღებთ სასწრაფო შემთხვევებს?",
                ),
                is_required=True,
            ),
            question(
                QuestionKey("home_visits"),
                Step.OFFER,
                Answer.YES_NO,
                text(
                    en="Do you make home visits?",
                    ru="Есть ли выезд на дом?",
                    ka="გაქვთ ბინაზე გამოძახება?",
                ),
            ),
            question(
                QuestionKey("visit_preparation"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
                text(
                    en="How should owners prepare an animal for a visit?",
                    ru="Как подготовить животное к приёму?",
                    ka="როგორ მოვამზადოთ ცხოველი ვიზიტისთვის?",
                ),
            ),
        ],
        prompt_rules=prompt_rules(
            "Never give veterinary advice, diagnoses or medication doses; you only "
            "book visits and share facts from the profile.",
            "If an animal is in danger (bleeding, poisoning, breathing problems, "
            "injury), tell the owner how to reach emergency care from the profile "
            "and hand off with critical urgency.",
            "Ask for the kind of animal and the service when booking.",
        ),
        example_exchanges=VETERINARY_EXAMPLES,
        default_handoff_rules=handoff_rules(
            en=[
                "Animal in danger or an emergency",
                "Question about a diagnosis, treatment or medication",
                "Complaint",
            ],
            ru=[
                "Животное в опасности или экстренный случай",
                "Вопрос о диагнозе, лечении или лекарствах",
                "Жалоба",
            ],
            ka=[
                "ცხოველი საფრთხეშია ან საგანგებო შემთხვევაა",
                "კითხვა დიაგნოზზე, მკურნალობაზე ან მედიკამენტებზე",
                "საჩივარი",
            ],
        ),
        default_forbidden_rules=forbidden_rules(
            en=["Veterinary advice, diagnoses or medication doses"],
            ru=["Ветеринарные советы, диагнозы и дозировки лекарств"],
            ka=["ვეტერინარული რჩევები, დიაგნოზები და მედიკამენტების დოზები"],
        ),
        autotest_kinds=autotest_kinds(AutotestScenarioKind.EMERGENCY),
    )
