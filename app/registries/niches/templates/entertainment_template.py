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


def build_entertainment_template() -> NicheTemplate:
    """VR, escape rooms, game and kids' centers: sessions and parties (wave A)."""

    return NicheTemplate(
        key=NicheKey.ENTERTAINMENT,
        wave=LaunchWave.A,
        names=text(
            en="VR, escape rooms, game and kids' centers",
            ru="VR, квесты, игровые и детские центры",
            ka="VR, ქვესტები, სათამაშო და საბავშვო ცენტრები",
        ),
        descriptions=text(
            en="Free slots, birthdays and corporate events (packages, "
            "prepayment), age limits and rules.",
            ru="Свободные слоты, дни рождения и корпоративы (пакеты, "
            "предоплата), возраст и правила.",
            ka="თავისუფალი სლოტები, დაბადების დღეები და კორპორატივები "
            "(პაკეტები, წინასწარი გადახდა), ასაკი და წესები.",
        ),
        recommended_plans=[PlanKey.CHAT, PlanKey.VOICE_AND_CHAT],
        resource_kind=ResourceKind.ARENA,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(
            en="arena or room",
            ru="арена или зал",
            ka="არენა ან დარბაზი",
        ),
        knowledge_kinds=[
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.PACKAGE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                QuestionKey("venue_type"),
                Step.NICHE_AND_LANGUAGES,
                Answer.SINGLE_CHOICE,
                text(
                    en="What kind of venue is it?",
                    ru="Какой у вас формат?",
                    ka="რა ფორმატის დაწესებულებაა?",
                ),
                is_required=True,
                choices=[
                    choice(Choice("vr_club"), "VR club", "VR-клуб", "VR კლუბი"),
                    choice(
                        Choice("escape_room"),
                        "Escape room",
                        "Квест-комната",
                        "ქვესტ-ოთახი",
                    ),
                    choice(
                        Choice("game_center"),
                        "Game center",
                        "Игровой центр",
                        "სათამაშო ცენტრი",
                    ),
                    choice(
                        Choice("kids_center"),
                        "Kids' center",
                        "Детский центр",
                        "საბავშვო ცენტრი",
                    ),
                    choice(Choice("other"), "Other", "Другое", "სხვა"),
                ],
            ),
            question(
                QuestionKey("min_age"),
                Step.FAQ_AND_HANDOFF,
                Answer.NUMBER,
                text(
                    en="Minimum age of players",
                    ru="Минимальный возраст игроков",
                    ka="მოთამაშეების მინიმალური ასაკი",
                ),
                is_required=True,
                hints=text(
                    en="Write 0 if there is no limit.",
                    ru="Укажите 0, если ограничений нет.",
                    ka="მიუთითეთ 0, თუ შეზღუდვა არ არის.",
                ),
            ),
            question(
                QuestionKey("visitor_rules"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
                text(
                    en="Rules for visitors (safety, clothing, health limits)",
                    ru="Правила для посетителей (безопасность, одежда, "
                    "ограничения по здоровью)",
                    ka="ვიზიტორების წესები (უსაფრთხოება, ჩაცმულობა, "
                    "ჯანმრთელობის შეზღუდვები)",
                ),
            ),
            question(
                QuestionKey("max_players_per_session"),
                Step.BOOKING_RULES,
                Answer.NUMBER,
                text(
                    en="How many players can play in one session?",
                    ru="Сколько игроков в одном сеансе?",
                    ka="რამდენი მოთამაშე თამაშობს ერთ სეანსზე?",
                ),
            ),
            question(
                QuestionKey("prepayment"),
                Step.BOOKING_RULES,
                Answer.SINGLE_CHOICE,
                text(
                    en="When is prepayment required?",
                    ru="Когда нужна предоплата?",
                    ka="როდის არის საჭირო წინასწარი გადახდა?",
                ),
                choices=[
                    choice(Choice("never"), "Never", "Не нужна", "არასდროს"),
                    choice(
                        Choice("groups_and_events"),
                        "For groups and events",
                        "Для групп и праздников",
                        "ჯგუფებისა და ღონისძიებებისთვის",
                    ),
                    choice(Choice("always"), "Always", "Всегда", "ყოველთვის"),
                ],
            ),
            question(
                QuestionKey("birthday_packages"),
                Step.OFFER,
                Answer.YES_NO,
                text(
                    en="Do you offer birthday packages?",
                    ru="Есть ли пакеты на день рождения?",
                    ka="გაქვთ დაბადების დღის პაკეტები?",
                ),
                hints=text(
                    en="Add each package with its price to the price list.",
                    ru="Каждый пакет с ценой добавьте в прайс.",
                ),
            ),
            question(
                QuestionKey("corporate_events"),
                Step.OFFER,
                Answer.YES_NO,
                text(
                    en="Do you host corporate events?",
                    ru="Проводите ли вы корпоративы?",
                    ka="ატარებთ კორპორატიულ ღონისძიებებს?",
                ),
            ),
        ],
        prompt_rules=prompt_rules(
            "Check free slots with check_availability before you suggest a time "
            "and book the exact arena or room for the whole session.",
            "State age limits and visitor rules only as written in the profile.",
            "For birthdays, corporate events and large groups, offer the packages "
            "from the price list, mention the prepayment rule and create a lead "
            "with the date, number of guests and wishes.",
        ),
        default_handoff_rules=handoff_rules(
            en=[
                "Complaint",
                "Corporate event or group over 15 people",
                "Birthday with wishes that are not in the packages",
                "Injury or safety incident",
            ],
            ru=[
                "Жалоба",
                "Корпоратив или группа больше 15 человек",
                "День рождения с пожеланиями вне пакетов",
                "Травма или происшествие с безопасностью",
            ],
            ka=[
                "საჩივარი",
                "კორპორატივი ან 15-ზე მეტი ადამიანის ჯგუფი",
                "დაბადების დღე სურვილებით, რომლებიც პაკეტებში არ არის",
                "ტრავმა ან უსაფრთხოების ინციდენტი",
            ],
        ),
        default_forbidden_rules=forbidden_rules(
            en=["Letting in visitors below the age limit"],
            ru=["Пускать посетителей младше возрастного ограничения"],
            ka=["ასაკობრივ ზღვარზე უმცროსი ვიზიტორების დაშვება"],
        ),
        autotest_kinds=autotest_kinds(),
        integrations=[
            IntegrationName("Google Calendar"),
            IntegrationName("Cal.com"),
        ],
    )
