from app.registries.niches.examples.hospitality_examples import RESTAURANT_EXAMPLES
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


def build_restaurant_template() -> NicheTemplate:
    """Restaurants and cafes: tables, menu, banquets, delivery link (wave A)."""

    return NicheTemplate(
        key=NicheKey.RESTAURANT,
        wave=LaunchWave.A,
        names=text(
            en="Restaurants and cafes",
            ru="Рестораны и кафе",
            ka="რესტორნები და კაფეები",
        ),
        descriptions=text(
            en="Table bookings, opening hours and menu, banquet and birthday "
            "requests, cancellations and changes, delivery link. Allergens only "
            "from the profile.",
            ru="Бронь стола, часы и меню, заявки на банкет и день рождения, "
            "отмена и перенос, ссылка на доставку. Про аллергены — только из "
            "анкеты.",
            ka="მაგიდის დაჯავშნა, სამუშაო საათები და მენიუ, ბანკეტისა და "
            "დაბადების დღის მოთხოვნები, გაუქმება და გადატანა, მიტანის ბმული. "
            "ალერგენებზე — მხოლოდ ანკეტიდან.",
        ),
        recommended_plans=[PlanKey.VOICE_AND_CHAT],
        resource_kind=ResourceKind.TABLE,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(en="table", ru="стол", ka="მაგიდა"),
        knowledge_kinds=[
            KnowledgeItemKind.MENU_ITEM,
            KnowledgeItemKind.PACKAGE,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                QuestionKey("cuisine"),
                Step.NICHE_AND_LANGUAGES,
                Answer.SHORT_TEXT,
                text(
                    en="What cuisine do you serve?",
                    ru="Какая у вас кухня?",
                    ka="რა სამზარეულო გაქვთ?",
                ),
                is_required=True,
                hints=text(
                    en="For example: Georgian, Italian, seafood.",
                    ru="Например: грузинская, итальянская, морепродукты.",
                    ka="მაგალითად: ქართული, იტალიური, ზღვის პროდუქტები.",
                ),
            ),
            question(
                QuestionKey("seating_capacity"),
                Step.BOOKING_RULES,
                Answer.NUMBER,
                text(
                    en="How many seats do you have in total?",
                    ru="Сколько всего посадочных мест?",
                    ka="სულ რამდენი დასაჯდომი ადგილი გაქვთ?",
                ),
                hints=text(
                    en="Tables themselves are added as resources; the total helps "
                    "to answer questions about groups.",
                    ru="Сами столы добавляются как ресурсы; общее число помогает "
                    "отвечать про группы.",
                ),
            ),
            question(
                QuestionKey("banquets"),
                Step.OFFER,
                Answer.SINGLE_CHOICE,
                text(
                    en="Do you host banquets and private events?",
                    ru="Проводите ли вы банкеты и закрытые мероприятия?",
                    ka="მასპინძლობთ ბანკეტებსა და დახურულ ღონისძიებებს?",
                ),
                choices=[
                    choice(Choice("no"), "No", "Нет", "არა"),
                    choice(
                        Choice("separate_hall"),
                        "Yes, in a separate hall",
                        "Да, в отдельном зале",
                        "დიახ, ცალკე დარბაზში",
                    ),
                    choice(
                        Choice("whole_venue"),
                        "Yes, the whole venue",
                        "Да, всё заведение целиком",
                        "დიახ, მთელი დაწესებულება",
                    ),
                ],
            ),
            question(
                QuestionKey("banquet_max_guests"),
                Step.OFFER,
                Answer.NUMBER,
                text(
                    en="Maximum number of banquet guests",
                    ru="Максимум гостей на банкете",
                    ka="ბანკეტის სტუმრების მაქსიმალური რაოდენობა",
                ),
            ),
            question(
                QuestionKey("delivery"),
                Step.OFFER,
                Answer.SINGLE_CHOICE,
                text(
                    en="Do you deliver?",
                    ru="Есть ли доставка?",
                    ka="გაქვთ მიტანის სერვისი?",
                ),
                hints=text(
                    en="Add the delivery link under Business → Links: the "
                    "assistant sends it instead of taking delivery orders.",
                    ru="Ссылку на доставку добавьте в разделе «Бизнес» → "
                    "«Ссылки»: помощник отправит её вместо приёма заказа.",
                    ka="მიტანის ბმული დაამატეთ განყოფილებაში «ბიზნესი» → "
                    "«ბმულები»: ასისტენტი მას გაგზავნის შეკვეთის მიღების ნაცვლად.",
                ),
                choices=[
                    choice(
                        Choice("none"),
                        "No delivery",
                        "Нет доставки",
                        "მიტანა არ გვაქვს",
                    ),
                    choice(
                        Choice("own_couriers"),
                        "Our own couriers",
                        "Свои курьеры",
                        "საკუთარი კურიერები",
                    ),
                    choice(
                        Choice("delivery_apps"),
                        "Through delivery apps",
                        "Через сервисы доставки",
                        "მიტანის სერვისებით",
                    ),
                ],
            ),
            question(
                QuestionKey("live_music"),
                Step.OFFER,
                Answer.SHORT_TEXT,
                text(
                    en="Live music: on which days and at what time?",
                    ru="Живая музыка: в какие дни и во сколько?",
                    ka="ცოცხალი მუსიკა: რომელ დღეებში და რომელ საათზე?",
                ),
                hints=text(
                    en="Leave it empty if there is none.",
                    ru="Оставьте пустым, если её нет.",
                    ka="დატოვეთ ცარიელი, თუ არ გაქვთ.",
                ),
            ),
            question(
                QuestionKey("kids_menu"),
                Step.OFFER,
                Answer.YES_NO,
                text(
                    en="Do you have a kids' menu?",
                    ru="Есть ли детское меню?",
                    ka="გაქვთ საბავშვო მენიუ?",
                ),
            ),
            question(
                QuestionKey("outdoor_seating"),
                Step.OFFER,
                Answer.YES_NO,
                text(
                    en="Do you have outdoor seating or a terrace?",
                    ru="Есть ли летняя веранда или терраса?",
                    ka="გაქვთ ღია ტერასა?",
                ),
            ),
            question(
                QuestionKey("dietary_options"),
                Step.OFFER,
                Answer.MULTIPLE_CHOICE,
                text(
                    en="Dietary options",
                    ru="Особые варианты блюд",
                    ka="სპეციალური კვების ვარიანტები",
                ),
                choices=[
                    choice(
                        Choice("vegetarian"),
                        "Vegetarian",
                        "Вегетарианские",
                        "ვეგეტარიანული",
                    ),
                    choice(Choice("vegan"), "Vegan", "Веганские", "ვეგანური"),
                    choice(
                        Choice("gluten_free"),
                        "Gluten-free",
                        "Без глютена",
                        "უგლუტენო",
                    ),
                    choice(Choice("halal"), "Halal", "Халяль", "ჰალალი"),
                    choice(Choice("kosher"), "Kosher", "Кошерные", "კოშერი"),
                ],
            ),
            question(
                QuestionKey("allergen_policy"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
                text(
                    en="What may the assistant say about allergens?",
                    ru="Что помощник может говорить об аллергенах?",
                    ka="რა შეუძლია თქვას ასისტენტმა ალერგენებზე?",
                ),
                hints=text(
                    en="The assistant repeats only this text and passes any other "
                    "allergy question to staff.",
                    ru="Помощник повторяет только этот текст, остальные вопросы об "
                    "аллергии передаёт сотруднику.",
                ),
            ),
        ],
        prompt_rules=prompt_rules(
            "Mention allergens and ingredients only as written in the profile or "
            "the knowledge base; pass any other allergy question to staff.",
            "A table booking needs a date, a time, the number of guests and a name.",
            "For banquets, birthdays and groups larger than the maximum party "
            "size, collect the date, number of guests, budget and wishes and "
            "create a lead instead of a booking.",
            "Do not take delivery orders yourself; send the delivery link when "
            "there is one.",
        ),
        example_exchanges=RESTAURANT_EXAMPLES,
        default_handoff_rules=handoff_rules(
            en=[
                "Complaint about food or service",
                "Banquet or group over 20 people",
                "Question about allergies that the profile does not answer",
            ],
            ru=[
                "Жалоба на еду или обслуживание",
                "Банкет или группа больше 20 человек",
                "Вопрос об аллергии, на который нет ответа в анкете",
            ],
            ka=[
                "საჩივარი კერძზე ან მომსახურებაზე",
                "ბანკეტი ან 20-ზე მეტი ადამიანის ჯგუფი",
                "კითხვა ალერგიაზე, რომელზეც ანკეტაში პასუხი არ არის",
            ],
        ),
        default_forbidden_rules=forbidden_rules(
            en=["Statements about allergens that are not in the profile"],
            ru=["Утверждения об аллергенах, которых нет в анкете"],
            ka=["განცხადებები ალერგენებზე, რომლებიც ანკეტაში არ არის"],
        ),
        autotest_kinds=autotest_kinds(),
        integrations=[
            IntegrationName("Google Calendar"),
            IntegrationName("Poster"),
            IntegrationName("Loyverse"),
        ],
    )
