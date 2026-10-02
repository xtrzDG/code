"""Fakes of the contracts the assembly slice depends on.

Registries hold a few countries, languages and niches; the conversation
engine, the voice platform, the call greeting and the tool catalog are
recording fakes that tests can program.
"""

import json
from collections.abc import Callable
from typing import cast

from app.contracts.assistant_assembly import AssistantToolCatalogContract
from app.contracts.conversation_flow import ConversationTurnOrchestratorContract
from app.contracts.llm import LlmAdapterContract
from app.contracts.operator_contract import OperatorContract
from app.contracts.registries import (
    CountryRegistryContract,
    LanguageRegistryContract,
    NicheTemplateRegistryContract,
)
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.contracts.voice_platform import VoiceAgentProvisionerAdapterContract
from app.schemas.constants.assistants import AssistantToolName, AutotestScenarioKind
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.localization import (
    CountryOnboardingStatus,
    DataRegion,
    LanguageTextSupport,
    LanguageVoiceSupport,
    LocalNumberProvisioning,
    OtpDeliveryChannel,
    TextDirection,
)
from app.schemas.constants.niches import (
    LaunchWave,
    NicheKey,
    ProfileWizardStep,
    QuestionAnswerType,
)
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.conversations import (
    AssistantReply,
    CallGreeting,
    CallGreetingRequest,
    InboundMessage,
    LlmRequest,
    LlmResponse,
    LlmToolDefinition,
    LlmToolResult,
)
from app.schemas.dto.localization import CountryProfile, LanguageProfile, LocalizedText
from app.schemas.dto.niches import NicheTemplate, QuestionChoice, QuestionDefinition
from app.schemas.dto.voice import VoiceAgentSpec
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ExternalServiceError,
    NotFoundError,
    UnknownCountryError,
    UnsupportedLanguageError,
)
from app.schemas.typings.assistants.strings import (
    LlmToolDescription,
    LlmToolInputSchemaJson,
    PromptRuleText,
    VoiceAgentId,
)
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText
from app.schemas.typings.localization.constrained_integers import CountryCallingCode
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    EmergencyNumber,
    LanguageTag,
    ScriptCode,
    TimezoneName,
)
from app.schemas.typings.localization.strings import (
    CountryDisplayName,
    LanguageDisplayName,
    LocalizedTextValue,
)
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.schemas.typings.profiles.constrained_strings import (
    FactKey,
    QuestionChoiceKey,
    QuestionKey,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken

NO_COST: CostMicroUsd = CostMicroUsd(0)
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


def build_country(
    country_code: str,
    english_name: str,
    calling_code: int,
    currency_code: str,
    timezone_name: str,
    languages: list[str],
    emergency_number: str,
) -> CountryProfile:
    return CountryProfile(
        country_code=CountryCode(country_code),
        english_name=CountryDisplayName(english_name),
        calling_code=CountryCallingCode(calling_code),
        currency_code=CurrencyCode(currency_code),
        timezones=[TimezoneName(timezone_name)],
        default_timezone=TimezoneName(timezone_name),
        default_customer_languages=[LanguageTag(tag) for tag in languages],
        default_owner_language=LanguageTag(languages[0]),
        emergency_number=EmergencyNumber(emergency_number),
        data_region=DataRegion.EU,
        onboarding_status=CountryOnboardingStatus.SUPPORTED,
        otp_delivery_channels=[OtpDeliveryChannel.SMS],
        local_number_provisioning=LocalNumberProvisioning.AVAILABLE,
    )


class FakeCountryRegistry(CountryRegistryContract):
    """Georgia, Italy, Japan, Israel and the United States."""

    def __init__(self) -> None:
        countries: list[CountryProfile] = [
            build_country("GE", "Georgia", 995, "GEL", "Asia/Tbilisi", ["ka"], "112"),
            build_country("IT", "Italy", 39, "EUR", "Europe/Rome", ["it"], "112"),
            build_country("JP", "Japan", 81, "JPY", "Asia/Tokyo", ["ja"], "110"),
            build_country("IL", "Israel", 972, "ILS", "Asia/Jerusalem", ["he"], "100"),
            build_country(
                "US", "United States", 1, "USD", "America/New_York", ["en"], "911"
            ),
        ]
        self._countries: dict[str, CountryProfile] = {
            str(country.country_code): country for country in countries
        }

    def get(self, country_code: CountryCode) -> CountryProfile:
        country: CountryProfile | None = self._countries.get(str(country_code))
        if country is None:
            raise UnknownCountryError(f"Unknown country {country_code}.")

        return country

    def list_all(self) -> list[CountryProfile]:
        return list(self._countries.values())


def build_language(
    tag: str,
    english_name: str,
    native_name: str,
    script: str,
    direction: TextDirection = TextDirection.LEFT_TO_RIGHT,
) -> LanguageProfile:
    return LanguageProfile(
        tag=LanguageTag(tag),
        english_name=LanguageDisplayName(english_name),
        native_name=LanguageDisplayName(native_name),
        script=ScriptCode(script),
        direction=direction,
        text_support=LanguageTextSupport.SUPPORTED,
        voice_support=LanguageVoiceSupport.VERIFIED,
    )


class FakeLanguageRegistry(LanguageRegistryContract):
    """A handful of languages in Latin, Georgian, Cyrillic, Hebrew, Arabic, Japanese."""

    def __init__(self) -> None:
        languages: list[LanguageProfile] = [
            build_language("ka", "Georgian", "ქართული", "Geor"),
            build_language("ru", "Russian", "русский", "Cyrl"),
            build_language("en", "English", "English", "Latn"),
            build_language("it", "Italian", "italiano", "Latn"),
            build_language("ja", "Japanese", "日本語", "Jpan"),
            build_language(
                "he", "Hebrew", "עברית", "Hebr", TextDirection.RIGHT_TO_LEFT
            ),
            build_language(
                "ar", "Arabic", "العربية", "Arab", TextDirection.RIGHT_TO_LEFT
            ),
        ]
        self._languages: dict[str, LanguageProfile] = {
            str(language.tag): language for language in languages
        }

    def get(self, language_tag: LanguageTag) -> LanguageProfile:
        language: LanguageProfile | None = self._languages.get(str(language_tag))
        if language is None:
            raise UnsupportedLanguageError(f"Unknown language {language_tag}.")

        return language

    def list_all(self) -> list[LanguageProfile]:
        return list(self._languages.values())


type ReplyResponder = Callable[[InboundMessage, int], AssistantReply]


class FakeConversationTurnOrchestrator(ConversationTurnOrchestratorContract):
    """
    Answers sandbox messages with a programmable responder. One conversation
    per channel user; every reply is stored as a message with `reply_cost`
    so autotests can sum the assistant's costs.
    """

    def __init__(
        self,
        responder: ReplyResponder,
        message_repo: MessageRepoContract,
        reply_cost: CostMicroUsd = NO_COST,
    ) -> None:
        self._responder: ReplyResponder = responder
        self._message_repo: MessageRepoContract = message_repo
        self._reply_cost: CostMicroUsd = reply_cost
        self._conversation_ids: dict[str, ConversationId] = {}
        self._turn_counts: dict[str, int] = {}
        self.inbound_messages: list[InboundMessage] = []

    def conversation_id_for(self, channel_user_id: str) -> ConversationId:
        return self._conversation_ids.setdefault(channel_user_id, ConversationId())

    def execute(self, input_data: InboundMessage) -> AssistantReply:
        self.inbound_messages.append(input_data)
        channel_user_id: str = str(input_data.channel_user_id)
        turn_index: int = self._turn_counts.get(channel_user_id, 0)
        self._turn_counts[channel_user_id] = turn_index + 1
        reply: AssistantReply = self._responder(input_data, turn_index)
        conversation_id: ConversationId = self.conversation_id_for(channel_user_id)
        reply = reply.model_copy(update={"conversation_id": conversation_id})
        self._message_repo.save(
            MessageDocument(
                conversation_id=conversation_id,
                business_id=input_data.business_id,
                direction=MessageDirection.OUTBOUND,
                author=MessageAuthor.ASSISTANT,
                text=reply.text or MessageText("(silent)"),
                cost_micro_usd=self._reply_cost,
            )
        )
        return reply


class FakeVoiceAgentProvisioner(VoiceAgentProvisionerAdapterContract):
    """Records every spec; returns the existing agent id or a new one."""

    def __init__(self) -> None:
        self.specs: list[VoiceAgentSpec] = []
        self.removed_agent_ids: list[VoiceAgentId] = []
        self.error: ExternalServiceError | None = None
        self.missing_settings: list[EnvironmentVariableName] = []
        self._created_count: int = 0

    def list_missing_settings(self) -> list[EnvironmentVariableName]:
        return list(self.missing_settings)

    def remove_agent(self, agent_id: VoiceAgentId) -> None:
        self.removed_agent_ids.append(agent_id)

    def upsert_agent(self, spec: VoiceAgentSpec) -> VoiceAgentId:
        self.specs.append(spec)
        if self.error is not None:
            raise self.error

        if spec.existing_agent_id is not None:
            return spec.existing_agent_id

        self._created_count += 1
        return VoiceAgentId(f"agent_{self._created_count}")


class FakeCallGreetingUseCase(UseCaseContract[CallGreetingRequest, CallGreeting]):
    """First phrase of a call; unknown languages fall back to English."""

    def __init__(self) -> None:
        self.requests: list[CallGreetingRequest] = []
        self.error: NotFoundError | None = None

    def run(self, input_data: CallGreetingRequest) -> CallGreeting:
        self.requests.append(input_data)
        if self.error is not None:
            raise self.error

        language: LanguageTag = input_data.language or LanguageTag("en")
        return CallGreeting(
            text=MessageText(f"[{language}] AI assistant here; the call is recorded."),
            language=language,
        )


class FakeAssistantToolCatalog(AssistantToolCatalogContract):
    """One trivial definition per tool, in the requested order."""

    def list_definitions(
        self,
        tool_names: list[AssistantToolName],
    ) -> list[LlmToolDefinition]:
        return [
            LlmToolDefinition(
                name=tool_name,
                description=LlmToolDescription(f"The {tool_name.value} tool."),
                input_schema_json=LlmToolInputSchemaJson('{"type": "object"}'),
            )
            for tool_name in tool_names
        ]


class FakeAuthenticationOperator(OperatorContract[AccessToken, UserId]):
    """Bearer tokens are "token-<user id>"."""

    def __init__(self) -> None:
        self._users: dict[str, UserId] = {}

    def register(self, user_id: UserId) -> str:
        token: str = f"token-{user_id}"
        self._users[token] = user_id
        return token

    def operate(self, input_data: AccessToken) -> UserId:
        user_id: UserId | None = self._users.get(str(input_data))
        if user_id is None:
            raise AuthenticationRequiredError("Unknown token.")

        return user_id


class TokenReportingLlmAdapter(LlmAdapterContract):
    """Wraps an adapter and reports fixed token counts on every response."""

    def __init__(
        self,
        inner_adapter: LlmAdapterContract,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        self._inner_adapter: LlmAdapterContract = inner_adapter
        self._input_tokens: LlmTokenCount = LlmTokenCount(input_tokens)
        self._output_tokens: LlmTokenCount = LlmTokenCount(output_tokens)

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        return self._inner_adapter.build_user_text_turn(text)

    def build_tool_results_turn(
        self,
        results: list[LlmToolResult],
    ) -> LlmProviderPayload:
        return self._inner_adapter.build_tool_results_turn(results)

    def complete(self, request: LlmRequest) -> LlmResponse:
        response: LlmResponse = self._inner_adapter.complete(request)
        return response.model_copy(
            update={
                "input_tokens": self._input_tokens,
                "output_tokens": self._output_tokens,
            }
        )


def read_last_user_text(request: LlmRequest) -> str:
    """Text of the last user turn of a request (canonical payload format)."""

    payload = cast(dict[str, object], json.loads(request.transcript[-1]))
    content = cast(list[dict[str, object]], payload["content"])
    return str(content[0]["text"])


def count_assistant_turns(request: LlmRequest) -> int:
    """How many model turns the transcript already holds."""

    return sum(
        1
        for payload in request.transcript
        if cast(dict[str, object], json.loads(payload))["role"] == "assistant"
    )
