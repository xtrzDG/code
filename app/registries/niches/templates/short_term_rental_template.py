from app.registries.niches.template_parts import (
    autotest_kinds,
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
from app.schemas.typings.profiles.constrained_strings import QuestionKey


def build_short_term_rental_template() -> NicheTemplate:
    """Short-term rental apartments: stays booked by nights (wave B)."""

    return NicheTemplate(
        key=NicheKey.SHORT_TERM_RENTAL,
        wave=LaunchWave.B,
        names=text(
            en="Short-term rental apartments",
            ru="Квартиры посуточно",
            ka="დღიურად გასაქირავებელი ბინები",
        ),
        descriptions=text(
            en="Questions before booking, check-in instructions, Wi-Fi, house "
            "rules and stay extensions in the guest's language.",
            ru="Вопросы до брони, инструкция по заселению, Wi-Fi, правила, "
            "продление — на языке гостя.",
            ka="კითხვები დაჯავშნამდე, შესახლების ინსტრუქცია, Wi-Fi, წესები და "
            "გახანგრძლივება — სტუმრის ენაზე.",
        ),
        recommended_plans=[PlanKey.CHAT],
        resource_kind=ResourceKind.ROOM,
        booking_unit=BookingUnit.NIGHT,
        resource_nouns=text(en="apartment", ru="квартира", ka="ბინა"),
        knowledge_kinds=[
            KnowledgeItemKind.ROOM_TYPE,
            KnowledgeItemKind.SERVICE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                QuestionKey("apartment_count"),
                Step.NICHE_AND_LANGUAGES,
                Answer.NUMBER,
                text(
                    en="How many apartments do you rent out?",
                    ru="Сколько квартир вы сдаёте?",
                    ka="რამდენ ბინას აქირავებთ?",
                ),
                is_required=True,
            ),
            question(
                QuestionKey("host_phone"),
                Step.CONTACTS_AND_HOURS,
                Answer.PHONE_NUMBER,
                text(
                    en="Phone for guests who are already staying",
                    ru="Телефон для гостей, которые уже заселились",
                    ka="ტელეფონი უკვე შესახლებული სტუმრებისთვის",
                ),
            ),
            question(
                QuestionKey("check_in_time"),
                Step.BOOKING_RULES,
                Answer.SHORT_TEXT,
                text(en="Check-in time", ru="Время заезда", ka="შესახლების დრო"),
                is_required=True,
            ),
            question(
                QuestionKey("check_out_time"),
                Step.BOOKING_RULES,
                Answer.SHORT_TEXT,
                text(en="Check-out time", ru="Время выезда", ka="გამოსახლების დრო"),
                is_required=True,
            ),
            question(
                QuestionKey("extension_policy"),
                Step.BOOKING_RULES,
                Answer.LONG_TEXT,
                text(
                    en="How can guests extend their stay?",
                    ru="Как продлить проживание?",
                    ka="როგორ შეიძლება ცხოვრების გახანგრძლივება?",
                ),
            ),
            question(
                QuestionKey("check_in_instructions"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
                text(
                    en="How do guests check in?",
                    ru="Как гости заселяются?",
                    ka="როგორ ხდება სტუმრების შესახლება?",
                ),
                hints=text(
                    en="Do not write door or safe codes here: the assistant shares "
                    "this text with anyone who asks.",
                    ru="Не пишите сюда коды от дверей и сейфов: помощник отправит "
                    "этот текст любому, кто спросит.",
                ),
            ),
            question(
                QuestionKey("wifi_info"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
                text(
                    en="Wi-Fi information for guests",
                    ru="Wi-Fi для гостей",
                    ka="Wi-Fi სტუმრებისთვის",
                ),
                hints=text(
                    en="The assistant shares this text with anyone who asks.",
                    ru="Помощник отправит этот текст любому, кто спросит.",
                ),
            ),
            question(
                QuestionKey("house_rules"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
                text(
                    en="House rules (smoking, parties, pets, quiet hours)",
                    ru="Правила проживания (курение, вечеринки, животные, тишина)",
                    ka="ცხოვრების წესები (მოწევა, წვეულებები, შინაური ცხოველები, "
                    "სიჩუმე)",
                ),
            ),
        ],
        prompt_rules=prompt_rules(
            "Apartments are booked by nights: confirm the check-in date, the "
            "number of nights and the number of guests before booking.",
            "Share check-in instructions, Wi-Fi details and house rules only as "
            "written in the profile.",
            "Never share door, lock-box or safe codes.",
            "If a guest cannot get in or something is broken, hand off to the host "
            "with high urgency.",
        ),
        default_handoff_rules=handoff_rules(
            en=[
                "A guest cannot get in",
                "Damage, breakdown or emergency in the apartment",
                "Complaint",
                "Stay longer than 30 nights",
            ],
            ru=[
                "Гость не может попасть в квартиру",
                "Поломка, ущерб или авария в квартире",
                "Жалоба",
                "Проживание дольше 30 ночей",
            ],
            ka=[
                "სტუმარი ვერ შედის ბინაში",
                "დაზიანება, გაფუჭება ან ავარია ბინაში",
                "საჩივარი",
                "30 ღამეზე მეტი ცხოვრება",
            ],
        ),
        default_forbidden_rules=forbidden_rules(
            en=["Sharing door, lock-box or safe codes"],
            ru=["Сообщать коды от дверей, ключниц и сейфов"],
            ka=["კარის, გასაღების ყუთის ან სეიფის კოდების გაზიარება"],
        ),
        autotest_kinds=autotest_kinds(),
        integrations=[IntegrationName("WhatsApp")],
    )
