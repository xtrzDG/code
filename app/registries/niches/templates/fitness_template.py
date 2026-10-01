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


def build_fitness_template() -> NicheTemplate:
    """Fitness, martial arts and padel: trials, classes, courts (wave B)."""

    return NicheTemplate(
        key=NicheKey.FITNESS,
        wave=LaunchWave.B,
        names=text(
            en="Fitness, martial arts and padel",
            ru="Фитнес, ММА и единоборства, падел",
            ka="ფიტნესი, საბრძოლო ხელოვნება და პადელი",
        ),
        descriptions=text(
            en="Trial sessions, class schedule, memberships and freezes, court rental.",
            ru="Пробная тренировка, расписание, абонементы, заморозка, аренда корта.",
            ka="საცდელი ვარჯიში, განრიგი, აბონემენტები და გაყინვა, კორტის ქირაობა.",
        ),
        recommended_plans=[PlanKey.CHAT],
        resource_kind=ResourceKind.SLOT,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(
            en="class or court",
            ru="занятие или корт",
            ka="ვარჯიში ან კორტი",
        ),
        knowledge_kinds=[
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.PACKAGE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                QuestionKey("activities"),
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
                        Choice("gym"),
                        "Gym",
                        "Тренажёрный зал",
                        "სავარჯიშო დარბაზი",
                    ),
                    choice(
                        Choice("group_classes"),
                        "Group classes",
                        "Групповые занятия",
                        "ჯგუფური ვარჯიშები",
                    ),
                    choice(
                        Choice("martial_arts"),
                        "Martial arts",
                        "Единоборства",
                        "საბრძოლო ხელოვნება",
                    ),
                    choice(Choice("padel"), "Padel", "Падел", "პადელი"),
                    choice(Choice("tennis"), "Tennis", "Теннис", "ჩოგბურთი"),
                    choice(Choice("yoga"), "Yoga", "Йога", "იოგა"),
                    choice(Choice("swimming"), "Swimming", "Плавание", "ცურვა"),
                ],
            ),
            question(
                QuestionKey("trial_session"),
                Step.OFFER,
                Answer.SINGLE_CHOICE,
                text(
                    en="Trial session",
                    ru="Пробная тренировка",
                    ka="საცდელი ვარჯიში",
                ),
                choices=[
                    choice(Choice("free"), "Free", "Бесплатная", "უფასო"),
                    choice(Choice("paid"), "Paid", "Платная", "ფასიანი"),
                    choice(Choice("none"), "Not available", "Нет", "არ არის"),
                ],
            ),
            question(
                QuestionKey("class_schedule"),
                Step.OFFER,
                Answer.LONG_TEXT,
                text(
                    en="Class schedule",
                    ru="Расписание занятий",
                    ka="ვარჯიშების განრიგი",
                ),
            ),
            question(
                QuestionKey("court_rental"),
                Step.OFFER,
                Answer.YES_NO,
                text(
                    en="Can courts or halls be rented?",
                    ru="Можно ли арендовать корт или зал?",
                    ka="შეიძლება კორტის ან დარბაზის ქირაობა?",
                ),
            ),
            question(
                QuestionKey("membership_freeze"),
                Step.BOOKING_RULES,
                Answer.LONG_TEXT,
                text(
                    en="Membership freeze rules",
                    ru="Правила заморозки абонемента",
                    ka="აბონემენტის გაყინვის წესები",
                ),
            ),
            question(
                QuestionKey("what_to_bring"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
                text(
                    en="What should visitors bring?",
                    ru="Что взять с собой?",
                    ka="რა წამოიღოს ვიზიტორმა?",
                ),
            ),
        ],
        prompt_rules=prompt_rules(
            "Book trial sessions and classes only into free slots from "
            "check_availability.",
            "Quote membership prices and freeze rules only from the profile and "
            "the price list.",
            "Do not give training, nutrition or health advice; suggest talking to "
            "a coach.",
        ),
        default_handoff_rules=handoff_rules(
            en=[
                "Injury or health problem during training",
                "Membership refund or dispute",
                "Corporate membership request",
            ],
            ru=[
                "Травма или проблема со здоровьем на тренировке",
                "Возврат денег за абонемент или спор",
                "Запрос корпоративного абонемента",
            ],
            ka=[
                "ტრავმა ან ჯანმრთელობის პრობლემა ვარჯიშისას",
                "აბონემენტის თანხის დაბრუნება ან დავა",
                "კორპორატიული აბონემენტის მოთხოვნა",
            ],
        ),
        default_forbidden_rules=forbidden_rules(
            en=["Training, nutrition or health advice"],
            ru=["Советы по тренировкам, питанию и здоровью"],
            ka=["რჩევები ვარჯიშზე, კვებასა და ჯანმრთელობაზე"],
        ),
        autotest_kinds=autotest_kinds(),
        integrations=[IntegrationName("Google Calendar")],
    )
