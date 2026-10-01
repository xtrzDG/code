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


def build_real_estate_template() -> NicheTemplate:
    """Real estate and developers: lead qualification and viewings (wave B)."""

    return NicheTemplate(
        key=NicheKey.REAL_ESTATE,
        wave=LaunchWave.B,
        names=text(
            en="Real estate and developers",
            ru="Недвижимость и застройщики",
            ka="უძრავი ქონება და დეველოპერები",
        ),
        descriptions=text(
            en="Lead qualification around the clock (budget, district, timeline, "
            "installments), viewing appointments, answers for foreign buyers.",
            ru="Квалификация заявок 24/7 (бюджет, район, срок, рассрочка), запись "
            "на показ, ответы иностранцам.",
            ka="მოთხოვნების კვალიფიკაცია 24/7 (ბიუჯეტი, რაიონი, ვადა, "
            "განვადება), ჩვენებაზე ჩაწერა, პასუხები უცხოელებს.",
        ),
        recommended_plans=[PlanKey.PLUS],
        resource_kind=ResourceKind.STAFF,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(
            en="viewing agent",
            ru="агент для показа",
            ka="აგენტი ჩვენებისთვის",
        ),
        knowledge_kinds=[
            KnowledgeItemKind.PRODUCT,
            KnowledgeItemKind.FAQ,
            KnowledgeItemKind.POLICY,
        ],
        questions=[
            question(
                QuestionKey("property_types"),
                Step.NICHE_AND_LANGUAGES,
                Answer.MULTIPLE_CHOICE,
                text(
                    en="What do you sell or rent?",
                    ru="Что вы продаёте или сдаёте?",
                    ka="რას ყიდით ან აქირავებთ?",
                ),
                is_required=True,
                choices=[
                    choice(Choice("apartments"), "Apartments", "Квартиры", "ბინები"),
                    choice(Choice("houses"), "Houses", "Дома", "სახლები"),
                    choice(
                        Choice("commercial"),
                        "Commercial property",
                        "Коммерческая недвижимость",
                        "კომერციული ფართი",
                    ),
                    choice(Choice("land"), "Land", "Земля", "მიწა"),
                ],
            ),
            question(
                QuestionKey("projects"),
                Step.OFFER,
                Answer.LONG_TEXT,
                text(
                    en="Projects and districts",
                    ru="Проекты и районы",
                    ka="პროექტები და რაიონები",
                ),
            ),
            question(
                QuestionKey("installment_plans"),
                Step.OFFER,
                Answer.LONG_TEXT,
                text(en="Installment plans", ru="Рассрочка", ka="განვადება"),
            ),
            question(
                QuestionKey("completion_dates"),
                Step.OFFER,
                Answer.LONG_TEXT,
                text(
                    en="Construction stages and completion dates",
                    ru="Этапы строительства и сроки сдачи",
                    ka="მშენებლობის ეტაპები და ჩაბარების ვადები",
                ),
            ),
            question(
                QuestionKey("foreign_buyers"),
                Step.FAQ_AND_HANDOFF,
                Answer.LONG_TEXT,
                text(
                    en="What should foreign buyers know?",
                    ru="Что важно знать иностранным покупателям?",
                    ka="რა უნდა იცოდნენ უცხოელმა მყიდველებმა?",
                ),
            ),
            question(
                QuestionKey("lead_fields"),
                Step.FAQ_AND_HANDOFF,
                Answer.MULTIPLE_CHOICE,
                text(
                    en="Which details should the assistant collect before passing "
                    "a lead?",
                    ru="Что помощник уточняет, прежде чем передать заявку?",
                    ka="რა დააზუსტოს ასისტენტმა მოთხოვნის გადაცემამდე?",
                ),
                choices=[
                    choice(Choice("budget"), "Budget", "Бюджет", "ბიუჯეტი"),
                    choice(Choice("district"), "District", "Район", "რაიონი"),
                    choice(
                        Choice("timeline"),
                        "Purchase timeline",
                        "Срок покупки",
                        "ყიდვის ვადა",
                    ),
                    choice(
                        Choice("installment"),
                        "Need for installments",
                        "Нужна ли рассрочка",
                        "განვადების საჭიროება",
                    ),
                    choice(
                        Choice("purpose"),
                        "Purpose: living or investment",
                        "Цель: жить или инвестиция",
                        "მიზანი: საცხოვრებლად თუ ინვესტიციისთვის",
                    ),
                ],
            ),
        ],
        prompt_rules=prompt_rules(
            "Qualify every buyer before passing the lead: ask for the details "
            "listed in the profile (budget, district, timeline, installments).",
            "Quote prices only as 'from' prices from the price list; a manager "
            "confirms which units are still available.",
            "Do not give legal, tax or investment advice and never promise returns "
            "or price growth.",
        ),
        default_handoff_rules=handoff_rules(
            en=[
                "Qualified buyer ready for a viewing or a deal",
                "Legal, tax or residency questions",
                "Complaint",
            ],
            ru=[
                "Квалифицированный покупатель готов к показу или сделке",
                "Юридические, налоговые вопросы или вопросы о ВНЖ",
                "Жалоба",
            ],
            ka=[
                "კვალიფიციური მყიდველი მზადაა ჩვენებისთვის ან გარიგებისთვის",
                "იურიდიული, საგადასახადო ან ბინადრობის კითხვები",
                "საჩივარი",
            ],
        ),
        default_forbidden_rules=forbidden_rules(
            en=["Legal, tax or investment advice; promises of returns"],
            ru=["Юридические, налоговые и инвестиционные советы; обещания доходности"],
            ka=[
                "იურიდიული, საგადასახადო და საინვესტიციო რჩევები; "
                "შემოსავლიანობის დაპირებები",
            ],
        ),
        autotest_kinds=autotest_kinds(),
        integrations=[IntegrationName("CRM"), IntegrationName("Google Sheets")],
    )
