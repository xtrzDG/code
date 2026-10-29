"""A niche template registry with a restaurant, a clinic and an online shop."""

from app.contracts.registries import NicheTemplateRegistryContract
from app.registries.niches.examples.hospitality_examples import RESTAURANT_EXAMPLES
from app.registries.niches.examples.trade_examples import ONLINE_SHOP_EXAMPLES
from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import (
    LaunchWave,
    NicheKey,
    ProfileWizardStep,
    QuestionAnswerType,
)
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.niches import NicheTemplate, QuestionChoice, QuestionDefinition
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.assistants.strings import PromptRuleText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.schemas.typings.profiles.constrained_strings import (
    FactKey,
    QuestionChoiceKey,
    QuestionKey,
)

ALL_BASE_KINDS: list[AutotestScenarioKind] = [
    AutotestScenarioKind.BOOKING,
    AutotestScenarioKind.BOOKING_OUT_OF_HOURS,
    AutotestScenarioKind.CANCELLATION,
    AutotestScenarioKind.PRICE_QUESTION,
    AutotestScenarioKind.UNKNOWN_QUESTION,
    AutotestScenarioKind.DISCOUNT_REQUEST,
    AutotestScenarioKind.RUDE_CUSTOMER,
    AutotestScenarioKind.HUMAN_REQUEST,
    AutotestScenarioKind.PROMPT_INJECTION,
]


def text(**values: str) -> LocalizedText:
    """LocalizedText from keyword arguments named by language tag."""

    return LocalizedText(
        values={
            LanguageTag(tag.replace("_", "-")): LocalizedTextValue(value)
            for tag, value in values.items()
        }
    )


def build_restaurant_template() -> NicheTemplate:
    """A restaurant niche with free-text, yes/no, choice and phone questions."""

    return NicheTemplate(
        key=NicheKey.RESTAURANT,
        wave=LaunchWave.A,
        names=text(en="Restaurants and cafes", ru="Рестораны и кафе"),
        descriptions=text(en="Tables, menu, banquets", ru="Столы, меню, банкеты"),
        recommended_plans=[PlanKey.VOICE_AND_CHAT],
        resource_kind=ResourceKind.TABLE,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(en="table", ru="стол"),
        knowledge_kinds=[KnowledgeItemKind.MENU_ITEM, KnowledgeItemKind.FAQ],
        questions=[
            QuestionDefinition(
                key=QuestionKey("live_music"),
                step=ProfileWizardStep.OFFER,
                answer_type=QuestionAnswerType.YES_NO,
                is_required=False,
                labels=text(en="Is there live music?", ru="Есть живая музыка?"),
                choices=[
                    QuestionChoice(key=QuestionChoiceKey("yes"), labels=text(en="Yes")),
                    QuestionChoice(key=QuestionChoiceKey("no"), labels=text(en="No")),
                ],
                fact_key=FactKey("live_music"),
            ),
            QuestionDefinition(
                key=QuestionKey("cuisine"),
                step=ProfileWizardStep.OFFER,
                answer_type=QuestionAnswerType.MULTIPLE_CHOICE,
                is_required=False,
                labels=text(en="Cuisine", ru="Кухня"),
                choices=[
                    QuestionChoice(
                        key=QuestionChoiceKey("georgian"),
                        labels=text(en="Georgian"),
                    ),
                    QuestionChoice(
                        key=QuestionChoiceKey("european"),
                        labels=text(en="European"),
                    ),
                ],
                fact_key=FactKey("cuisine"),
            ),
            QuestionDefinition(
                key=QuestionKey("banquet_manager_phone"),
                step=ProfileWizardStep.FAQ_AND_HANDOFF,
                answer_type=QuestionAnswerType.PHONE_NUMBER,
                is_required=False,
                labels=text(en="Banquet manager phone", ru="Телефон банкетов"),
                fact_key=FactKey("banquet_phone"),
            ),
            QuestionDefinition(
                key=QuestionKey("kids_menu"),
                step=ProfileWizardStep.OFFER,
                answer_type=QuestionAnswerType.SHORT_TEXT,
                is_required=False,
                labels=text(en="Kids menu", ru="Детское меню"),
                fact_key=FactKey("kids_menu"),
            ),
        ],
        prompt_rules=[
            PromptRuleText("Offer the menu link when customers ask what to eat."),
            PromptRuleText("Never promise a table that check_availability did not."),
        ],
        example_exchanges=RESTAURANT_EXAMPLES,
        default_handoff_rules=text(
            en="Banquet over 20 people\nAllergy question",
            ru="Банкет больше 20 человек\nВопрос об аллергии",
        ),
        default_forbidden_rules=text(
            en="Discounts or special prices without approval\nPromises beyond "
            "the profile",
            ru="Скидки без согласования\nОбещания сверх анкеты",
        ),
        autotest_kinds=list(ALL_BASE_KINDS),
    )


def build_clinic_template() -> NicheTemplate:
    """A clinic niche: strict medical rules and an emergency scenario."""

    return NicheTemplate(
        key=NicheKey.CLINIC,
        wave=LaunchWave.B,
        names=text(en="Clinics and dentists", ru="Клиники и стоматологии"),
        descriptions=text(en="Doctors and visits", ru="Врачи и приёмы"),
        recommended_plans=[PlanKey.VOICE_AND_CHAT],
        resource_kind=ResourceKind.STAFF,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text(en="doctor's appointment", ru="приём врача"),
        knowledge_kinds=[KnowledgeItemKind.SERVICE, KnowledgeItemKind.FAQ],
        questions=[],
        prompt_rules=[
            PromptRuleText(
                "Never give medical advice, diagnoses or medication "
                "recommendations; you only book visits."
            ),
        ],
        default_handoff_rules=text(
            en="Urgent symptoms or an emergency\nComplaint",
            ru="Срочные симптомы\nЖалоба",
        ),
        default_forbidden_rules=text(
            en="Medical advice, diagnoses or medication recommendations",
            ru="Медицинские советы",
        ),
        autotest_kinds=[*ALL_BASE_KINDS, AutotestScenarioKind.EMERGENCY],
        requires_legal_review=True,
    )


def build_online_shop_template() -> NicheTemplate:
    """An online shop: no bookings, orders are taken as leads."""

    return NicheTemplate(
        key=NicheKey.ONLINE_SHOP,
        wave=LaunchWave.C,
        names=text(en="Online shops", ru="Интернет-магазины"),
        descriptions=text(en="Orders and delivery", ru="Заказы и доставка"),
        recommended_plans=[PlanKey.CHAT],
        resource_kind=ResourceKind.SLOT,
        booking_unit=BookingUnit.TIME_SLOT,
        takes_bookings=False,
        resource_nouns=text(en="", ru=""),
        knowledge_kinds=[KnowledgeItemKind.PRODUCT],
        questions=[],
        prompt_rules=[],
        example_exchanges=ONLINE_SHOP_EXAMPLES,
        default_handoff_rules=text(en="", ru=""),
        default_forbidden_rules=text(en="", ru=""),
        autotest_kinds=list(ALL_BASE_KINDS),
    )


class FakeNicheTemplateRegistry(NicheTemplateRegistryContract):
    """Restaurant, clinic and online shop templates."""

    def __init__(self) -> None:
        self._templates: dict[NicheKey, NicheTemplate] = {
            template.key: template
            for template in (
                build_restaurant_template(),
                build_clinic_template(),
                build_online_shop_template(),
            )
        }

    def get(self, niche_key: NicheKey) -> NicheTemplate:
        template: NicheTemplate | None = self._templates.get(niche_key)
        if template is None:
            raise NotFoundError(f"Niche {niche_key} is not in the fake registry.")

        return template

    def list_all(self) -> list[NicheTemplate]:
        return list(self._templates.values())
