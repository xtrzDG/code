from app.registries.niches.examples.service_examples import EDUCATION_EXAMPLES
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


def build_education_template() -> NicheTemplate:
    """Schools, courses, clubs and driving schools: trial lessons (wave C)."""

    return NicheTemplate(
        key=NicheKey.EDUCATION,
        wave=LaunchWave.C,
        names=text(
            en="Schools, courses, clubs and driving schools",
            ru="Школы, курсы, кружки и автошколы",
            ka="სკოლები, კურსები, წრეები და ავტოსკოლები",
        ),
        descriptions=text(
            en="Trial lessons, schedule, prices, sign-up and payment reminders.",
            ru="Пробное занятие, расписание, цены, запись, напоминания об оплате.",
            ka="საცდელი გაკვეთილი, განრიგი, ფასები, ჩაწერა და გადახდის შეხსენებები.",
        ),
        recommended_plans=[PlanKey.CHAT],
        resource_kind=ResourceKind.SLOT,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(en="lesson", ru="занятие", ka="გაკვეთილი"),
        knowledge_kinds=[
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.PACKAGE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                QuestionKey("subjects"),
                Step.NICHE_AND_LANGUAGES,
                Answer.SHORT_TEXT,
                text(
                    en="What do you teach?",
                    ru="Чему вы учите?",
                    ka="რას ასწავლით?",
                ),
                is_required=True,
            ),
            question(
                QuestionKey("age_groups"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                text(
                    en="Age groups",
                    ru="Возрастные группы",
                    ka="ასაკობრივი ჯგუფები",
                ),
                choices=[
                    choice(Choice("kids"), "Children", "Дети", "ბავშვები"),
                    choice(Choice("teens"), "Teenagers", "Подростки", "მოზარდები"),
                    choice(Choice("adults"), "Adults", "Взрослые", "ზრდასრულები"),
                ],
            ),
            question(
                QuestionKey("trial_lesson"),
                Step.OFFER,
                Answer.SINGLE_CHOICE,
                text(
                    en="Trial lesson",
                    ru="Пробное занятие",
                    ka="საცდელი გაკვეთილი",
                ),
                choices=[
                    choice(Choice("free"), "Free", "Бесплатное", "უფასო"),
                    choice(Choice("paid"), "Paid", "Платное", "ფასიანი"),
                    choice(Choice("none"), "Not available", "Нет", "არ არის"),
                ],
            ),
            question(
                QuestionKey("lesson_formats"),
                Step.OFFER,
                Answer.MULTIPLE_CHOICE,
                text(
                    en="Lesson formats",
                    ru="Форматы занятий",
                    ka="გაკვეთილების ფორმატები",
                ),
                choices=[
                    choice(Choice("group"), "Group", "В группе", "ჯგუფური"),
                    choice(
                        Choice("individual"),
                        "Individual",
                        "Индивидуально",
                        "ინდივიდუალური",
                    ),
                    choice(Choice("online"), "Online", "Онлайн", "ონლაინ"),
                ],
            ),
            question(
                QuestionKey("group_schedule"),
                Step.OFFER,
                Answer.LONG_TEXT,
                text(
                    en="Schedule of groups",
                    ru="Расписание групп",
                    ka="ჯგუფების განრიგი",
                ),
            ),
            question(
                QuestionKey("payment_terms"),
                Step.BOOKING_RULES,
                Answer.LONG_TEXT,
                text(
                    en="Payment terms",
                    ru="Условия оплаты",
                    ka="გადახდის პირობები",
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
                        Choice("student_age"),
                        "Student's age",
                        "Возраст ученика",
                        "მოსწავლის ასაკი",
                    ),
                    choice(
                        Choice("level"),
                        "Current level",
                        "Текущий уровень",
                        "ამჟამინდელი დონე",
                    ),
                    choice(
                        Choice("preferred_time"),
                        "Preferred time",
                        "Удобное время",
                        "სასურველი დრო",
                    ),
                    choice(Choice("format"), "Format", "Формат", "ფორმატი"),
                ],
            ),
        ],
        prompt_rules=prompt_rules(
            "Sign students up for trial lessons only into free slots from "
            "check_availability.",
            "Quote course prices and payment terms only from the profile and the "
            "price list.",
            "Do not promise exam results or certificates that are not in the profile.",
        ),
        example_exchanges=EDUCATION_EXAMPLES,
        default_handoff_rules=handoff_rules(
            en=[
                "Payment dispute or refund",
                "Student with special needs",
                "Complaint",
            ],
            ru=[
                "Спор об оплате или возврат",
                "Ученик с особыми потребностями",
                "Жалоба",
            ],
            ka=[
                "დავა გადახდაზე ან თანხის დაბრუნება",
                "მოსწავლე განსაკუთრებული საჭიროებებით",
                "საჩივარი",
            ],
        ),
        default_forbidden_rules=forbidden_rules(
            en=["Promising exam results"],
            ru=["Обещания результатов экзаменов"],
            ka=["გამოცდის შედეგების დაპირება"],
        ),
        autotest_kinds=autotest_kinds(),
    )
