"""Fakes and an in-memory wiring of the channels slice, shared by its tests.

Platforms are reached through the real HTTP clients over recording
`httpx.MockTransport`s; the conversation engine, the voice tool runner and
the greeting builder are fakes implementing their contracts. Phone numbers,
languages and texts use the real localization utilities (no network).
"""

import hashlib
import hmac
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx
import httpx2
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typed_time_provider import Microseconds, WallClock

from app.adapters.channels.instagram_channel_adapter import InstagramChannelAdapter
from app.adapters.channels.messenger_channel_adapter import MessengerChannelAdapter
from app.adapters.channels.telegram_channel_adapter import TelegramChannelAdapter
from app.adapters.channels.whatsapp_channel_adapter import WhatsAppChannelAdapter
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.adapters.voice.elevenlabs_voice_webhook_adapter import (
    ElevenLabsVoiceWebhookAdapter,
)
from app.clients.elevenlabs.elevenlabs_client import ElevenLabsClient
from app.clients.meta.meta_graph_client import MetaGraphClient
from app.clients.telegram.telegram_bot_client import TelegramBotClient
from app.contracts.conversation_flow import (
    CustomerMessagePipelineContract,
    VoiceToolCallOrchestratorContract,
)
from app.contracts.operator_contract import OperatorContract
from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.facilitators.channels.channel_message_sender_facilitator import (
    ChannelMessageSenderFacilitator,
)
from app.gateways.http.channel_routes import build_channel_router
from app.gateways.http.channel_settings_routes import build_channel_settings_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.user_authentication import build_current_user_dependency
from app.gateways.http.voice_routes import build_voice_router
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.channels.channel_webhook_orchestrator import (
    ChannelWebhookOrchestrator,
)
from app.orchestrators.channels.post_call_webhook_orchestrator import (
    PostCallWebhookOrchestrator,
)
from app.orchestrators.channels.voice_tool_webhook_orchestrator import (
    VoiceToolWebhookOrchestrator,
)
from app.orchestrators.channels.widget_message_orchestrator import (
    WidgetMessageOrchestrator,
)
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.registries.billing.plan_registry import PlanRegistry
from app.registries.limits.request_rate_limit_registry import (
    RequestRateLimitRegistry,
)
from app.registries.localization.language_registry import LanguageRegistry
from app.repositories.assistant_repositories import AssistantVersionRepository
from app.repositories.billing_repositories import UsageEventRepository
from app.repositories.booking_repositories import (
    BookingRepository,
    HandoffRepository,
    LeadRepository,
)
from app.repositories.business_repositories import (
    BusinessProfileRepository,
    BusinessRepository,
    ChannelRepository,
)
from app.repositories.channel_repositories import (
    ChannelMessageReceiptRepository,
    ManagerTelegramLinkRepository,
)
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.conversation_repositories import (
    CallRepository,
    ContactRepository,
    ConversationRepository,
    MessageRepository,
)
from app.repositories.knowledge_repositories import ScheduleExceptionRepository
from app.repositories.user_repositories import UserRepository
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.channels import ChannelKind, ChannelStatus, MessageDirection
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.channel_receipts import ChannelMessageReceiptDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.manager_links import ManagerTelegramLinkDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.conversations import (
    AssistantReply,
    CallGreeting,
    CallGreetingRequest,
    InboundMessage,
    VoiceToolCallRequest,
    VoiceToolCallResult,
)
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ValidationFailedError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    ChannelSecret,
    EncryptedChannelSecret,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import LlmToolResultJson, MessageText
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.channels.accept_widget_message_use_case import (
    AcceptWidgetMessageUseCase,
)
from app.use_cases.channels.build_widget_reply_use_case import BuildWidgetReplyUseCase
from app.use_cases.channels.connect_channel_use_case import ConnectChannelUseCase
from app.use_cases.channels.create_telegram_link_use_case import (
    CreateTelegramLinkUseCase,
)
from app.use_cases.channels.deliver_channel_reply_use_case import (
    DeliverChannelReplyUseCase,
)
from app.use_cases.channels.disable_channel_use_case import DisableChannelUseCase
from app.use_cases.channels.get_widget_config_use_case import GetWidgetConfigUseCase
from app.use_cases.channels.get_widget_messages_use_case import (
    GetWidgetMessagesUseCase,
)
from app.use_cases.channels.get_widget_snippet_use_case import GetWidgetSnippetUseCase
from app.use_cases.channels.handle_platform_bot_update_use_case import (
    HandlePlatformBotUpdateUseCase,
)
from app.use_cases.channels.list_channels_use_case import ListChannelsUseCase
from app.use_cases.channels.receive_meta_webhook_use_case import (
    ReceiveMetaWebhookUseCase,
)
from app.use_cases.channels.receive_telegram_webhook_use_case import (
    ReceiveTelegramWebhookUseCase,
)
from app.use_cases.channels.set_whatsapp_staff_template_use_case import (
    SetWhatsAppStaffTemplateUseCase,
)
from app.use_cases.channels.verify_meta_webhook_use_case import (
    VerifyMetaWebhookUseCase,
)
from app.use_cases.voice.authenticate_post_call_use_case import (
    AuthenticatePostCallUseCase,
)
from app.use_cases.voice.authenticate_voice_tool_call_use_case import (
    AuthenticateVoiceToolCallUseCase,
)
from app.use_cases.voice.record_finished_call_use_case import (
    RecordFinishedCallUseCase,
)
from app.use_cases.voice.send_call_confirmation_use_case import (
    SendCallConfirmationUseCase,
)
from app.use_cases.voice.start_voice_call_use_case import StartVoiceCallUseCase
from app.utilities.config_helpers.app_settings_assembler import assemble_app_settings
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from app.utilities.storage.storage_scope_context import StorageScopeContext

# Responses of FastAPI's TestClient (built on httpx2).
HttpResponse = httpx2.Response
NANOSECONDS_PER_SECOND: int = 1_000_000_000
# 2026-10-01 12:00:00 UTC.
START_UNIX_SECONDS: int = 1_790_856_000
APP_BASE_URL: str = "https://api.workshop.test"
META_APP_SECRET: str = "meta-app-secret-for-tests"
META_VERIFY_TOKEN: str = "meta-verify-token-for-tests"
WHATSAPP_SYSTEM_TOKEN: str = "whatsapp-system-user-token"
PLATFORM_BOT_TOKEN: str = "700000001:PLATFORMbotTOKENfortestsPLATFORMbotTOKEN"
ELEVENLABS_WEBHOOK_SECRET: str = "elevenlabs-webhook-secret-for-tests"
ENCRYPTION_KEY: str = "an-encryption-key-that-is-long-enough-for-tests"
TELEGRAM_BOT_TOKEN: str = "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
OTHER_TELEGRAM_BOT_TOKEN: str = "987654321:BBHdqTcvCH1vGWJxfSeofSAs0K5PALDsbx"
PAGE_ACCESS_TOKEN: str = "EAAGpageAccessTokenForTests0123456789"

TEST_ENVIRONMENT: dict[str, str] = {
    "APP_ENV": "test",
    "APP_BASE_URL": APP_BASE_URL,
    "ENCRYPTION_KEY": ENCRYPTION_KEY,
    "META_APP_SECRET": META_APP_SECRET,
    "META_VERIFY_TOKEN": META_VERIFY_TOKEN,
    "WHATSAPP_SYSTEM_USER_TOKEN": WHATSAPP_SYSTEM_TOKEN,
    "WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID": "900000000000001",
    "WHATSAPP_NOTIFICATION_TEMPLATE": "staff_notification",
    "TELEGRAM_PLATFORM_BOT_TOKEN": PLATFORM_BOT_TOKEN,
    "ELEVENLABS_API_KEY": "elevenlabs-api-key",
    "ELEVENLABS_WEBHOOK_SECRET": ELEVENLABS_WEBHOOK_SECRET,
}


def build_settings(**overrides: str) -> AppSettings:
    """Test settings; an override with an empty value removes the variable."""

    environment: dict[str, str] = {**TEST_ENVIRONMENT, **overrides}
    return assemble_app_settings(
        {name: value for name, value in environment.items() if value != ""}
    )


class RecordingVoiceAgentRemoval:
    """Records the businesses whose voice agent was switched off."""

    def __init__(self, business_ids: list[BusinessId]) -> None:
        self.business_ids: list[BusinessId] = business_ids

    def run(self, input_data: BusinessId) -> None:
        self.business_ids.append(input_data)


class AdjustableClock:
    """Unix time that tests move forward explicitly."""

    def __init__(self, start_seconds: int = START_UNIX_SECONDS) -> None:
        self.nanoseconds: int = start_seconds * NANOSECONDS_PER_SECOND

    def read(self) -> int:
        return self.nanoseconds

    def advance(self, seconds: int) -> None:
        self.nanoseconds += seconds * NANOSECONDS_PER_SECOND

    def advance_microseconds(self, microseconds: int) -> None:
        self.nanoseconds += microseconds * 1000

    def build_wall_clock(self) -> WallClock[Microseconds]:
        return WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=self.read,
        )

    def now_seconds(self) -> int:
        return self.nanoseconds // NANOSECONDS_PER_SECOND

    def now_microseconds(self) -> Microseconds:
        return Microseconds(self.nanoseconds // 1000)


class FakeSecretCipher(SecretCipherAdapterContract):
    """Reversible stand-in for the Fernet cipher; ciphertext never equals plaintext."""

    PREFIX: str = "sealed:"

    def encrypt(self, secret: ChannelSecret) -> EncryptedChannelSecret:
        return EncryptedChannelSecret(self.PREFIX + str(secret)[::-1])

    def decrypt(self, encrypted_secret: EncryptedChannelSecret) -> ChannelSecret:
        text: str = str(encrypted_secret)
        if not text.startswith(self.PREFIX):
            raise ValidationFailedError("Invalid ciphertext.")

        return ChannelSecret(text.removeprefix(self.PREFIX)[::-1])


class ScriptedCustomerPipeline(CustomerMessagePipelineContract):
    """
    Engine stand-in: answers "Reply: <text>", stays silent or fails. Like the
    engine it stores the conversation of each customer (the first one gets
    `conversation_id`) with the customer's message and the answer.
    """

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        clock: AdjustableClock,
    ) -> None:
        self.messages: list[InboundMessage] = []
        self.is_silent: bool = False
        self.failure: ApplicationError | None = None
        self.language: LanguageTag = LanguageTag("en")
        self.reply_text: str | None = None
        self.conversation_id: ConversationId = ConversationId()
        self._conversation_repo: ConversationRepository = conversation_repo
        self._message_repo: MessageRepository = message_repo
        self._clock: AdjustableClock = clock
        self._is_first_used: bool = False

    def start(self, input_data: InboundMessage) -> AssistantReply:
        self.messages.append(input_data)
        if self.failure is not None:
            raise self.failure

        text: MessageText | None = None
        if not self.is_silent:
            text = MessageText(self.reply_text or f"Reply: {input_data.text}")

        conversation: ConversationDocument = self._conversation_of(input_data)
        self._store(conversation, MessageAuthor.CUSTOMER, input_data.text)
        if text is not None:
            self._store(conversation, MessageAuthor.ASSISTANT, text)

        return AssistantReply(
            conversation_id=conversation.id,
            text=text,
            language=self.language,
            is_handed_off=self.is_silent,
        )

    def _conversation_of(self, message: InboundMessage) -> ConversationDocument:
        now: Microseconds = self._clock.now_microseconds()
        status: ConversationStatus = (
            ConversationStatus.HANDOFF if self.is_silent else ConversationStatus.OPEN
        )
        for conversation in self._conversation_repo.list_by_business(
            message.business_id
        ):
            if (
                conversation.channel is message.channel
                and conversation.channel_user_id == message.channel_user_id
            ):
                conversation.status = status
                conversation.last_message_at = now
                self._conversation_repo.save(conversation)
                return conversation

        conversation = ConversationDocument(
            id=ConversationId() if self._is_first_used else self.conversation_id,
            business_id=message.business_id,
            contact_id=ContactId(),
            assistant_version_id=AssistantVersionId(),
            channel=message.channel,
            channel_user_id=message.channel_user_id,
            language=self.language,
            status=status,
            last_message_at=now,
            created_at=now,
            updated_at=now,
        )
        self._is_first_used = True
        self._conversation_repo.save(conversation)
        return conversation

    def _store(
        self,
        conversation: ConversationDocument,
        author: MessageAuthor,
        text: MessageText,
    ) -> None:
        now: Microseconds = self._clock.now_microseconds()
        self._message_repo.save(
            MessageDocument(
                conversation_id=conversation.id,
                business_id=conversation.business_id,
                direction=(
                    MessageDirection.INBOUND
                    if author is MessageAuthor.CUSTOMER
                    else MessageDirection.OUTBOUND
                ),
                author=author,
                text=text,
                language=self.language,
                created_at=now,
                updated_at=now,
            )
        )
        # Each stored message gets its own instant, like real traffic.
        self._clock.advance_microseconds(1)


class FakeVoiceToolCallOrchestrator(VoiceToolCallOrchestratorContract):
    def __init__(self) -> None:
        self.requests: list[VoiceToolCallRequest] = []

    def execute(self, input_data: VoiceToolCallRequest) -> VoiceToolCallResult:
        self.requests.append(input_data)
        return VoiceToolCallResult(
            result_json=LlmToolResultJson(
                json.dumps({"ok": True, "tool": input_data.tool_name.value})
            )
        )


class FakeCallGreetingUseCase(UseCaseContract[CallGreetingRequest, CallGreeting]):
    def __init__(self, business_repo: BusinessRepository) -> None:
        self._business_repo: BusinessRepository = business_repo
        self.requests: list[CallGreetingRequest] = []

    def run(self, input_data: CallGreetingRequest) -> CallGreeting:
        self.requests.append(input_data)
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        assert business is not None
        language: LanguageTag = input_data.language or business.default_language
        return CallGreeting(
            text=MessageText(f"[{language}] AI assistant of {business.name}."),
            language=language,
        )


class FakeAuthenticationOperator(OperatorContract[AccessToken, UserId]):
    def __init__(self) -> None:
        self.users_by_token: dict[str, UserId] = {}

    def operate(self, input_data: AccessToken) -> UserId:
        user_id: UserId | None = self.users_by_token.get(str(input_data))
        if user_id is None:
            raise AuthenticationRequiredError("Unknown token.")

        return user_id


@dataclass
class RecordedRequest:
    method: str
    url: httpx.URL
    headers: httpx.Headers
    body: bytes

    @property
    def path(self) -> str:
        return self.url.path

    def json(self) -> Any:
        return json.loads(self.body) if self.body else None


@dataclass
class ScriptedRoute:
    method: str
    path_pattern: re.Pattern[str]
    responses: list[tuple[int, object]]


@dataclass
class RecordingTransport:
    """httpx.MockTransport that answers scripted routes and records requests."""

    routes: list[ScriptedRoute] = field(default_factory=list[ScriptedRoute])
    requests: list[RecordedRequest] = field(default_factory=list[RecordedRequest])
    failure: Exception | None = None

    def respond(
        self,
        method: str,
        path_pattern: str,
        body: object,
        status_code: int = 200,
    ) -> None:
        """Answer matching requests; the newest script for a route wins."""

        self.routes.insert(
            0,
            ScriptedRoute(
                method=method,
                path_pattern=re.compile(path_pattern),
                responses=[(status_code, body)],
            ),
        )

    def build(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def requests_to(self, path_fragment: str) -> list[RecordedRequest]:
        return [request for request in self.requests if path_fragment in request.path]

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(
            RecordedRequest(
                method=request.method,
                url=request.url,
                headers=request.headers,
                body=request.content,
            )
        )
        if self.failure is not None:
            raise self.failure

        for route in self.routes:
            if route.method == request.method and route.path_pattern.search(
                request.url.path
            ):
                status_code, body = route.responses[0]
                return httpx.Response(status_code, json=body)

        return httpx.Response(404, json={"error": "not scripted"})


def telegram_ok(result: object = True) -> dict[str, object]:
    return {"ok": True, "result": result}


def sign_meta(body: bytes, secret: str = META_APP_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def sign_elevenlabs(
    body: bytes,
    timestamp: int,
    secret: str = ELEVENLABS_WEBHOOK_SECRET,
) -> str:
    message: bytes = str(timestamp).encode() + b"." + body
    digest: str = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f"t={timestamp},v0={digest}"


def to_json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class CountrySetup:
    """Defaults of a business in one country (taken from its country profile)."""

    country_code: str
    timezone: str
    currency_code: str
    languages: tuple[str, ...]


GEORGIA = CountrySetup("GE", "Asia/Tbilisi", "GEL", ("ka", "ru", "en"))
ISRAEL = CountrySetup("IL", "Asia/Jerusalem", "ILS", ("he", "ar", "en"))
POLAND = CountrySetup("PL", "Europe/Warsaw", "PLN", ("pl", "en"))
BRAZIL = CountrySetup("BR", "America/Sao_Paulo", "BRL", ("pt-BR", "en"))
KAZAKHSTAN = CountrySetup("KZ", "Asia/Almaty", "KZT", ("kk", "ru", "en"))
ARMENIA = CountrySetup("AM", "Asia/Yerevan", "AMD", ("hy", "ru", "en"))
UNITED_STATES = CountrySetup("US", "America/New_York", "USD", ("en", "es"))


class ChannelsTestbed:
    """Repositories, fakes and every channels component, wired in memory."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings: AppSettings = settings or build_settings()
        self.clock: AdjustableClock = AdjustableClock()
        self.wall_clock: WallClock[Microseconds] = self.clock.build_wall_clock()
        self.business_repo = BusinessRepository(
            InMemoryDocumentCollectionAdapter(BusinessDocument)
        )
        self.user_repo = UserRepository(InMemoryDocumentCollectionAdapter(UserDocument))
        self.channel_repo = ChannelRepository(
            InMemoryDocumentCollectionAdapter(ChannelDocument)
        )
        self.contact_repo = ContactRepository(
            InMemoryDocumentCollectionAdapter(ContactDocument)
        )
        self.conversation_repo = ConversationRepository(
            InMemoryDocumentCollectionAdapter(ConversationDocument)
        )
        self.message_repo = MessageRepository(
            InMemoryDocumentCollectionAdapter(MessageDocument)
        )
        self.call_repo = CallRepository(InMemoryDocumentCollectionAdapter(CallDocument))
        self.booking_repo = BookingRepository(
            InMemoryDocumentCollectionAdapter(BookingDocument)
        )
        self.lead_repo = LeadRepository(InMemoryDocumentCollectionAdapter(LeadDocument))
        self.handoff_repo = HandoffRepository(
            InMemoryDocumentCollectionAdapter(HandoffDocument)
        )
        self.usage_event_repo = UsageEventRepository(
            InMemoryDocumentCollectionAdapter(UsageEventDocument)
        )
        self.audit_log_repo = AuditLogRepository(
            InMemoryDocumentCollectionAdapter(AuditLogEntryDocument)
        )
        self.profile_repo = BusinessProfileRepository(
            InMemoryDocumentCollectionAdapter(BusinessProfileDocument)
        )
        self.exception_repo = ScheduleExceptionRepository(
            InMemoryDocumentCollectionAdapter(ScheduleExceptionDocument)
        )
        self.assistant_version_repo = AssistantVersionRepository(
            InMemoryDocumentCollectionAdapter(AssistantVersionDocument)
        )
        self.receipt_repo = ChannelMessageReceiptRepository(
            InMemoryDocumentCollectionAdapter(ChannelMessageReceiptDocument)
        )
        self.link_repo = ManagerTelegramLinkRepository(
            InMemoryDocumentCollectionAdapter(ManagerTelegramLinkDocument)
        )

        self.secret_cipher = FakeSecretCipher()
        self.widget_rate_limits = RequestRateLimitRegistry()
        self.phone_number_parser = PhoneNumberParser()
        self.language_registry = LanguageRegistry()
        self.text_resolver = LocalizedTextResolver()
        self.pipeline = ScriptedCustomerPipeline(
            self.conversation_repo, self.message_repo, self.clock
        )
        self.voice_tool_orchestrator = FakeVoiceToolCallOrchestrator()
        self.call_greeting = FakeCallGreetingUseCase(self.business_repo)
        self.authentication = FakeAuthenticationOperator()

        self.telegram_transport = RecordingTransport()
        self.meta_transport = RecordingTransport()
        self.elevenlabs_transport = RecordingTransport()
        self.telegram_client = TelegramBotClient(
            transport=self.telegram_transport.build()
        )
        self.meta_client = MetaGraphClient(transport=self.meta_transport.build())
        self.elevenlabs_client = ElevenLabsClient(
            api_key=PlatformSecret("elevenlabs-api-key"),
            base_url=self.settings.elevenlabs_api_base_url,
            transport=self.elevenlabs_transport.build(),
        )

        self.telegram_adapter = TelegramChannelAdapter(
            self.telegram_client, self.phone_number_parser, self.settings
        )
        self.whatsapp_adapter = WhatsAppChannelAdapter(
            self.meta_client, self.phone_number_parser, self.settings
        )
        self.messenger_adapter = MessengerChannelAdapter(
            self.meta_client, self.settings
        )
        self.instagram_adapter = InstagramChannelAdapter(
            self.meta_client, self.settings
        )
        self.voice_webhook_adapter = ElevenLabsVoiceWebhookAdapter(self.settings)

        self.authorize_business_access = AuthorizeBusinessAccessUseCase(
            self.business_repo, self.user_repo, self.audit_log_repo, self.wall_clock
        )
        self.channel_message_sender = ChannelMessageSenderFacilitator(
            self.channel_repo,
            self.secret_cipher,
            self.telegram_adapter,
            self.whatsapp_adapter,
            self.messenger_adapter,
            self.instagram_adapter,
            self.whatsapp_adapter,
            self.usage_event_repo,
            self.wall_clock,
        )
        self.deliver_reply = DeliverChannelReplyUseCase(
            self.telegram_adapter,
            self.whatsapp_adapter,
            self.messenger_adapter,
            self.instagram_adapter,
            self.usage_event_repo,
            self.channel_repo,
            self.wall_clock,
        )
        self.receive_telegram_webhook = ReceiveTelegramWebhookUseCase(
            self.channel_repo,
            self.secret_cipher,
            self.telegram_adapter,
            self.receipt_repo,
            self.wall_clock,
        )
        self.receive_meta_webhook = ReceiveMetaWebhookUseCase(
            self.channel_repo,
            self.secret_cipher,
            self.whatsapp_adapter,
            self.messenger_adapter,
            self.instagram_adapter,
            self.receipt_repo,
            self.wall_clock,
        )
        self.connect_channel = ConnectChannelUseCase(
            self.authorize_business_access,
            self.channel_repo,
            self.secret_cipher,
            self.telegram_client,
            self.meta_client,
            self.phone_number_parser,
            self.audit_log_repo,
            self.settings,
            self.wall_clock,
            StorageScopeContext(),
        )
        self.voice_agent_removals: list[BusinessId] = []
        self.disable_channel = DisableChannelUseCase(
            self.authorize_business_access,
            self.channel_repo,
            self.secret_cipher,
            self.telegram_client,
            self.audit_log_repo,
            self.wall_clock,
            RecordingVoiceAgentRemoval(self.voice_agent_removals),
        )
        self.set_whatsapp_staff_template = SetWhatsAppStaffTemplateUseCase(
            self.authorize_business_access,
            self.channel_repo,
            self.audit_log_repo,
            self.wall_clock,
        )
        self.list_channels = ListChannelsUseCase(
            self.authorize_business_access, self.channel_repo
        )
        self.create_telegram_link = CreateTelegramLinkUseCase(
            self.authorize_business_access,
            self.link_repo,
            self.language_registry,
            self.telegram_client,
            self.settings,
            self.wall_clock,
        )
        self.handle_platform_bot_update = HandlePlatformBotUpdateUseCase(
            self.link_repo,
            self.business_repo,
            self.audit_log_repo,
            self.telegram_client,
            self.text_resolver,
            self.settings,
            self.wall_clock,
        )
        self.record_finished_call = RecordFinishedCallUseCase(
            self.channel_repo,
            self.business_repo,
            self.assistant_version_repo,
            self.conversation_repo,
            self.call_repo,
            self.booking_repo,
            self.lead_repo,
            self.handoff_repo,
            self.usage_event_repo,
            self.audit_log_repo,
            self.phone_number_parser,
            self.wall_clock,
        )
        self.send_call_confirmation = SendCallConfirmationUseCase(
            self.business_repo,
            self.booking_repo,
            self.contact_repo,
            self.channel_repo,
            self.channel_message_sender,
            self.text_resolver,
        )

    # --- HTTP -----------------------------------------------------------

    def build_http_client(self) -> TestClient:
        http_application = FastAPI()
        install_error_handlers(http_application)
        http_application.include_router(
            build_channel_router(
                telegram_webhook_operator=wrap(
                    ChannelWebhookOrchestrator(
                        self.receive_telegram_webhook,
                        self.pipeline,
                        self.deliver_reply,
                    )
                ),
                meta_webhook_verification_operator=wrap_use_case(
                    VerifyMetaWebhookUseCase(self.settings)
                ),
                meta_webhook_operator=wrap(
                    ChannelWebhookOrchestrator(
                        self.receive_meta_webhook,
                        self.pipeline,
                        self.deliver_reply,
                    )
                ),
                platform_bot_webhook_operator=wrap_use_case(
                    self.handle_platform_bot_update
                ),
                widget_config_operator=wrap_use_case(
                    GetWidgetConfigUseCase(
                        self.business_repo,
                        self.channel_repo,
                        self.assistant_version_repo,
                        self.language_registry,
                    )
                ),
                widget_message_operator=wrap(
                    WidgetMessageOrchestrator(
                        AcceptWidgetMessageUseCase(
                            self.business_repo,
                            self.channel_repo,
                            self.widget_rate_limits,
                            self.wall_clock,
                        ),
                        self.pipeline,
                        BuildWidgetReplyUseCase(
                            self.message_repo, self.language_registry
                        ),
                    )
                ),
                widget_messages_operator=wrap_use_case(
                    GetWidgetMessagesUseCase(
                        self.business_repo,
                        self.channel_repo,
                        self.conversation_repo,
                        self.message_repo,
                        self.language_registry,
                        self.widget_rate_limits,
                        self.wall_clock,
                    )
                ),
            )
        )
        http_application.include_router(
            build_channel_settings_router(
                list_channels_operator=wrap_use_case(self.list_channels),
                connect_channel_operator=wrap_use_case(self.connect_channel),
                disable_channel_operator=wrap_use_case(self.disable_channel),
                widget_snippet_operator=wrap_use_case(
                    GetWidgetSnippetUseCase(
                        self.authorize_business_access, self.settings
                    )
                ),
                create_telegram_link_operator=wrap_use_case(self.create_telegram_link),
                current_user=build_current_user_dependency(self.authentication),
                set_whatsapp_staff_template_operator=wrap_use_case(
                    self.set_whatsapp_staff_template
                ),
            )
        )
        http_application.include_router(
            build_voice_router(
                voice_tool_operator=wrap(
                    VoiceToolWebhookOrchestrator(
                        AuthenticateVoiceToolCallUseCase(
                            self.business_repo,
                            self.voice_webhook_adapter,
                            self.phone_number_parser,
                            self.settings,
                        ),
                        self.voice_tool_orchestrator,
                    )
                ),
                call_initiation_operator=wrap_use_case(
                    StartVoiceCallUseCase(
                        self.business_repo,
                        self.assistant_version_repo,
                        self.channel_repo,
                        PlanRegistry(),
                        self.profile_repo,
                        self.exception_repo,
                        self.wall_clock,
                        self.voice_webhook_adapter,
                        self.phone_number_parser,
                        self.call_greeting,
                        self.settings,
                    )
                ),
                post_call_operator=wrap(
                    PostCallWebhookOrchestrator(
                        AuthenticatePostCallUseCase(
                            self.voice_webhook_adapter, self.wall_clock
                        ),
                        self.record_finished_call,
                        self.send_call_confirmation,
                    )
                ),
            )
        )
        return TestClient(http_application)

    # --- Data builders --------------------------------------------------

    def add_user(self, token: str, locale: str = "en") -> UserId:
        user = UserDocument(
            login_method=LoginMethod.PHONE,
            locale=LanguageTag(locale),
            is_verified=True,
        )
        self.user_repo.save(user)
        self.authentication.users_by_token[token] = user.id
        return user.id

    def add_business(
        self,
        owner_id: UserId,
        country: CountrySetup = GEORGIA,
        name: str = "Funicular VR",
        staff_ids: list[UserId] | None = None,
        owner_language: str | None = None,
    ) -> BusinessDocument:
        members: list[BusinessMember] = [
            BusinessMember(user_id=owner_id, role=BusinessMemberRole.OWNER)
        ]
        members.extend(
            BusinessMember(user_id=staff_id, role=BusinessMemberRole.STAFF)
            for staff_id in staff_ids or []
        )
        languages: list[LanguageTag] = [LanguageTag(tag) for tag in country.languages]
        business = BusinessDocument(
            name=BusinessName(name),
            niche_key=NicheKey.ENTERTAINMENT,
            country_code=CountryCode(country.country_code),
            timezone=TimezoneName(country.timezone),
            currency_code=CurrencyCode(country.currency_code),
            languages=languages,
            default_language=languages[0],
            owner_language=LanguageTag(owner_language or country.languages[0]),
            plan_key=PlanKey.VOICE_AND_CHAT,
            data_region=DataRegion.EU,
            members=members,
        )
        self.business_repo.save(business)
        return business

    def add_channel(
        self,
        business_id: BusinessId,
        kind: ChannelKind,
        external_id: str | None = None,
        secret: str | None = None,
        status: ChannelStatus = ChannelStatus.CONNECTED,
    ) -> ChannelDocument:
        channel = ChannelDocument(
            business_id=business_id,
            kind=kind,
            external_id=None if external_id is None else ChannelExternalId(external_id),
            encrypted_secret=(
                None
                if secret is None
                else self.secret_cipher.encrypt(ChannelSecret(secret))
            ),
            status=status,
        )
        self.channel_repo.save(channel)
        return channel

    def audit_actions(self, business_id: BusinessId) -> list[tuple[str, str]]:
        return [
            (entry.action.value, str(entry.entity))
            for entry in self.audit_log_repo.list_by_business(business_id)
        ]


def wrap[InputData, OutputData](
    orchestrator: OrchestratorContract[InputData, OutputData],
) -> PipelineOperator[InputData, OutputData]:
    """Operator -> pipeline -> the given orchestrator (the generic chain)."""

    return PipelineOperator(OrchestratorPipeline(orchestrator))


def wrap_use_case[InputData, OutputData](
    use_case: UseCaseContract[InputData, OutputData],
) -> PipelineOperator[InputData, OutputData]:
    """Operator -> pipeline -> orchestrator -> the given use case."""

    return PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(use_case)))


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def headers_with(extra: Mapping[str, str]) -> dict[str, str]:
    return {"Content-Type": "application/json", **extra}
