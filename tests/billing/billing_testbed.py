"""In-memory wiring of the billing slice shared by its tests.

Real registries (plans with the GEL price book, official rates), real
localization utilities, in-memory repositories, a recording notifier, an
adjustable clock and a Flitt sandbox behind httpx.MockTransport that checks
request signatures like Flitt does. Nothing touches the network.
"""

import base64
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typed_time_provider import Microseconds, WallClock

from app.adapters.payments.flitt_payment_gateway_adapter import (
    FlittPaymentGatewayAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.clients.flitt.flitt_client import FlittClient
from app.clients.flitt.flitt_protocol import build_parameter_signature
from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.operator_contract import OperatorContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.gateways.http.admin_routes import build_admin_router
from app.gateways.http.billing_routes import build_billing_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.user_authentication import build_current_user_dependency
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.billing.subscribe_orchestrator import SubscribeOrchestrator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.registries.billing.exchange_rate_registry import ExchangeRateRegistry
from app.registries.billing.plan_registry import PlanRegistry
from app.repositories.assistant_repositories import (
    AssistantVersionRepository,
    AutotestRunRepository,
)
from app.repositories.billing_repositories import (
    InvoiceRepository,
    SubscriptionRepository,
    UsageEventRepository,
)
from app.repositories.booking_repositories import (
    HandoffRepository,
    UnansweredQuestionRepository,
)
from app.repositories.business_repositories import BusinessRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.conversation_repositories import MessageRepository
from app.repositories.payment_repositories import (
    PackageUsageWarningRepository,
    PaymentOrderRepository,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.billing import PlanKey, UsageKind
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.domain.billing import (
    InvoiceDocument,
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.domain.businesses import (
    BusinessDocument,
    BusinessMember,
    ManagerContact,
)
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.domain.package_usage import PackageUsageWarningDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.dto.billing_ledger import BillingNotice, InvoiceDescriptionInput
from app.schemas.dto.catalog.plan_quotes import ExchangeRateQuote
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.payments import PaymentWebhookDelivery, PaymentWebhookReceipt
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.billing.constrained_floats import ExchangeRate
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    MoneyAmountMinor,
    UsageQuantity,
)
from app.schemas.typings.billing.constrained_strings import ExchangeRateDate
from app.schemas.typings.billing.strings import (
    ExchangeRateSourceName,
    PaymentWebhookBody,
    PaymentWebhookContentType,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken, UserDisplayName
from app.transformers.billing.billing_notice_transformer import (
    BillingNoticeTransformer,
)
from app.transformers.billing.invoice_description_transformer import (
    InvoiceDescriptionTransformer,
)
from app.use_cases.admin.authorize_platform_admin_use_case import (
    AuthorizePlatformAdminUseCase,
)
from app.use_cases.admin.get_client_health_use_case import GetClientHealthUseCase
from app.use_cases.admin.list_clients_use_case import ListClientsUseCase
from app.use_cases.admin.open_client_cabinet_use_case import (
    OpenClientCabinetUseCase,
)
from app.use_cases.admin.summarize_client_use_case import SummarizeClientUseCase
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.billing.assemble_billing_overview_use_case import (
    AssembleBillingOverviewUseCase,
)
from app.use_cases.billing.cancel_subscription_use_case import (
    CancelSubscriptionUseCase,
)
from app.use_cases.billing.change_plan_use_case import ChangePlanUseCase
from app.use_cases.billing.check_package_usage_use_case import (
    CheckPackageUsageUseCase,
)
from app.use_cases.billing.compute_client_cost_use_case import (
    ComputeClientCostUseCase,
)
from app.use_cases.billing.end_trials_use_case import EndTrialsUseCase
from app.use_cases.billing.enforce_grace_periods_use_case import (
    EnforceGracePeriodsUseCase,
)
from app.use_cases.billing.get_billing_overview_use_case import (
    GetBillingOverviewUseCase,
)
from app.use_cases.billing.invoice_usage_overage_use_case import (
    InvoiceUsageOverageUseCase,
)
from app.use_cases.billing.issue_due_invoices_use_case import (
    IssueDueInvoicesUseCase,
)
from app.use_cases.billing.open_subscription_use_case import (
    OpenSubscriptionUseCase,
)
from app.use_cases.billing.process_payment_webhook_use_case import (
    ProcessPaymentWebhookUseCase,
)
from app.use_cases.billing.start_checkout_use_case import StartCheckoutUseCase
from app.use_cases.billing.start_trial_use_case import StartTrialUseCase
from app.utilities.config_helpers.app_settings_assembler import assemble_app_settings
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver

# 2026-10-01 09:00 UTC, the concept's date.
START_NANOSECONDS: int = 1_790_845_200_000_000_000
NANOSECONDS_PER_MICROSECOND: int = 1_000
MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000
MICROSECONDS_PER_HOUR: int = 60 * 60 * 1_000_000
FLITT_MERCHANT_ID: str = "1549901"
FLITT_SECRET_KEY: str = "test"
APP_BASE_URL: str = "https://api.assistant.example"
CABINET_ORIGIN: str = "https://app.assistant.example"
CHECKOUT_URL: str = "https://pay.flitt.com/merchants/test/default/index.html?token=t1"


class RecordingVoiceAgentRemoval:
    """Records the businesses whose voice agent was switched off."""

    def __init__(self) -> None:
        self.business_ids: list[BusinessId] = []

    def run(self, input_data: BusinessId) -> None:
        self.business_ids.append(input_data)


@dataclass(frozen=True)
class CountryPreset:
    """Country defaults a business would get at creation."""

    country_code: str
    currency_code: str
    timezone: str
    owner_language: str
    languages: tuple[str, ...]


GEORGIA = CountryPreset("GE", "GEL", "Asia/Tbilisi", "ka", ("ka", "ru", "en"))
ITALY = CountryPreset("IT", "EUR", "Europe/Rome", "it", ("it", "en"))
USA = CountryPreset("US", "USD", "America/New_York", "en", ("en", "es"))
JAPAN = CountryPreset("JP", "JPY", "Asia/Tokyo", "ja", ("ja", "en"))
ISRAEL = CountryPreset("IL", "ILS", "Asia/Jerusalem", "he", ("he", "ar", "en"))
KAZAKHSTAN = CountryPreset("KZ", "KZT", "Asia/Almaty", "ru", ("kk", "ru"))


class PriceBookPlanRegistry(PlanRegistryContract):
    """
    The real plans with an extra price book, e.g. yen prices for Japan or
    odd amounts that exercise rounding.
    """

    def __init__(
        self,
        monthly_prices: dict[tuple[PlanKey, str], int],
        setup_fees: dict[tuple[PlanKey, str], int] | None = None,
    ) -> None:
        self._plans = PlanRegistry()
        self._monthly_prices: dict[tuple[PlanKey, str], int] = monthly_prices
        self._setup_fees: dict[tuple[PlanKey, str], int] = setup_fees or {}

    def get(self, plan_key: PlanKey) -> PlanDefinition:
        return self._plans.get(plan_key)

    def list_all(self) -> list[PlanDefinition]:
        return self._plans.list_all()

    def find_local_monthly_price(
        self,
        plan_key: PlanKey,
        currency_code: CurrencyCode,
    ) -> Money | None:
        amount: int | None = self._monthly_prices.get((plan_key, str(currency_code)))
        if amount is None:
            return self._plans.find_local_monthly_price(plan_key, currency_code)

        return Money(amount_minor=MoneyAmountMinor(amount), currency_code=currency_code)

    def find_local_setup_fee(
        self,
        plan_key: PlanKey,
        currency_code: CurrencyCode,
    ) -> Money | None:
        amount: int | None = self._setup_fees.get((plan_key, str(currency_code)))
        if amount is None:
            return self._plans.find_local_setup_fee(plan_key, currency_code)

        return Money(amount_minor=MoneyAmountMinor(amount), currency_code=currency_code)


class StaticExchangeRateRegistry(ExchangeRateRegistryContract):
    """Official rates given by the test."""

    def __init__(self, rates: list[tuple[str, str, float]]) -> None:
        self._quotes: list[ExchangeRateQuote] = [
            ExchangeRateQuote(
                base_currency_code=CurrencyCode(base),
                quote_currency_code=CurrencyCode(quote),
                rate=ExchangeRate(rate),
                rate_date=ExchangeRateDate("2026-09-30"),
                source=ExchangeRateSourceName("Test central bank"),
            )
            for base, quote, rate in rates
        ]

    def find_rate(
        self,
        base_currency_code: CurrencyCode,
        quote_currency_code: CurrencyCode,
    ) -> ExchangeRateQuote | None:
        for quote in self._quotes:
            if (
                quote.base_currency_code == base_currency_code
                and quote.quote_currency_code == quote_currency_code
            ):
                return quote

        return None

    def list_all(self) -> list[ExchangeRateQuote]:
        return list(self._quotes)


class AdjustableClock:
    """Wall clock whose time tests move forward explicitly."""

    def __init__(self, unix_nanoseconds: int = START_NANOSECONDS) -> None:
        self.unix_nanoseconds: int = unix_nanoseconds
        self.wall_clock: WallClock[Microseconds] = WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: self.unix_nanoseconds,
        )

    def now(self) -> Microseconds:
        return Microseconds(self.unix_nanoseconds // NANOSECONDS_PER_MICROSECOND)

    def advance(self, days: float = 0, hours: float = 0) -> None:
        self.unix_nanoseconds += int(
            (days * MICROSECONDS_PER_DAY + hours * MICROSECONDS_PER_HOUR)
            * NANOSECONDS_PER_MICROSECOND
        )

    def move_to(self, instant: Microseconds) -> None:
        self.unix_nanoseconds = int(instant) * NANOSECONDS_PER_MICROSECOND


class RecordingNotifier(ManagerNotificationFacilitatorContract):
    """Keeps every notification; delivery can be switched off."""

    def __init__(self) -> None:
        self.sent: list[tuple[ManagerContact, MessageText]] = []
        self.is_delivering: bool = True

    def notify(self, contact: ManagerContact, text: MessageText) -> bool:
        self.sent.append((contact, text))
        return self.is_delivering

    def texts(self) -> list[str]:
        return [str(text) for _, text in self.sent]


@dataclass
class FlittSandbox:
    """Flitt API stand-in that verifies protocol 2.0 request signatures."""

    checkout_orders: list[dict[str, object]] = field(
        default_factory=list[dict[str, object]]
    )
    stopped_orders: list[str] = field(default_factory=list[str])
    refusal: dict[str, object] | None = None
    http_status: int = 200

    def handle(self, request: httpx.Request) -> httpx.Response:
        envelope: dict[str, object] = json.loads(request.content)["request"]
        data: str = str(envelope["data"])
        expected = hashlib.sha1(f"{FLITT_SECRET_KEY}|{data}".encode()).hexdigest()
        if envelope["signature"] != expected or envelope["version"] != "2.0":
            return httpx.Response(
                200,
                json={
                    "response": {
                        "response_status": "failure",
                        "error_message": "Invalid signature",
                        "error_code": 1014,
                    }
                },
            )

        order: dict[str, object] = json.loads(base64.b64decode(data))["order"]
        if self.http_status != 200:
            return httpx.Response(self.http_status, text="unavailable")

        if self.refusal is not None:
            return httpx.Response(200, json={"response": self.refusal})

        if request.url.path == "/api/subscription/":
            self.stopped_orders.append(str(order["order_id"]))
            return httpx.Response(
                200, json={"response": {"response_status": "success"}}
            )

        self.checkout_orders.append(order)
        return httpx.Response(
            200,
            json={
                "response": {
                    "response_status": "success",
                    "checkout_url": CHECKOUT_URL,
                    "payment_id": 802345671,
                }
            },
        )


class TokenAuthenticationOperator(OperatorContract[AccessToken, UserId]):
    """Bearer token = user id of a known user (tests only)."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo: UserRepository = user_repo

    def operate(self, input_data: AccessToken) -> UserId:
        try:
            user_id = UserId(str(input_data))
        except ValueError as error:
            raise AuthenticationRequiredError("Unknown token.") from error

        if self._user_repo.get(user_id) is None:
            raise AuthenticationRequiredError("Unknown token.")

        return user_id


def build_operator[InputData, OutputData](
    use_case: UseCaseContract[InputData, OutputData],
) -> PipelineOperator[InputData, OutputData]:
    return PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(use_case)))


def build_settings() -> AppSettings:
    return assemble_app_settings(
        {
            "APP_ENV": "test",
            "APP_BASE_URL": APP_BASE_URL,
            "CORS_ALLOWED_ORIGINS": CABINET_ORIGIN,
            "FLITT_MERCHANT_ID": FLITT_MERCHANT_ID,
            "FLITT_SECRET_KEY": FLITT_SECRET_KEY,
        }
    )


def sign_flitt_callback(parameters: dict[str, object]) -> dict[str, object]:
    signed: dict[str, object] = dict(parameters)
    signed["signature"] = build_parameter_signature(FLITT_SECRET_KEY, signed)
    return signed


class BillingTestbed:
    """Every billing and admin use case over in-memory storage."""

    def __init__(
        self,
        plan_registry: PlanRegistryContract | None = None,
        exchange_rate_registry: ExchangeRateRegistryContract | None = None,
    ) -> None:
        self.clock = AdjustableClock()
        self.notifier = RecordingNotifier()
        self.flitt = FlittSandbox()
        self.settings: AppSettings = build_settings()
        self.plan_registry: PlanRegistryContract = plan_registry or PlanRegistry()
        self.exchange_rate_registry: ExchangeRateRegistryContract = (
            exchange_rate_registry or ExchangeRateRegistry()
        )
        resolver = LocalizedTextResolver()
        wall_clock: WallClock[Microseconds] = self.clock.wall_clock
        self.user_repo = UserRepository(
            InMemoryDocumentCollectionAdapter[UserDocument](UserDocument)
        )
        self.business_repo = BusinessRepository(
            InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
        )
        self.subscription_repo = SubscriptionRepository(
            InMemoryDocumentCollectionAdapter[SubscriptionDocument](
                SubscriptionDocument
            )
        )
        self.invoice_repo = InvoiceRepository(
            InMemoryDocumentCollectionAdapter[InvoiceDocument](InvoiceDocument)
        )
        self.usage_event_repo = UsageEventRepository(
            InMemoryDocumentCollectionAdapter[UsageEventDocument](UsageEventDocument)
        )
        self.payment_order_repo = PaymentOrderRepository(
            InMemoryDocumentCollectionAdapter[PaymentOrderDocument](
                PaymentOrderDocument
            )
        )
        self.warning_repo = PackageUsageWarningRepository(
            InMemoryDocumentCollectionAdapter[PackageUsageWarningDocument](
                PackageUsageWarningDocument
            )
        )
        self.audit_log_repo = AuditLogRepository(
            InMemoryDocumentCollectionAdapter[AuditLogEntryDocument](
                AuditLogEntryDocument
            )
        )
        self.message_repo = MessageRepository(
            InMemoryDocumentCollectionAdapter[MessageDocument](MessageDocument)
        )
        self.handoff_repo = HandoffRepository(
            InMemoryDocumentCollectionAdapter[HandoffDocument](HandoffDocument)
        )
        self.question_repo = UnansweredQuestionRepository(
            InMemoryDocumentCollectionAdapter[UnansweredQuestionDocument](
                UnansweredQuestionDocument
            )
        )
        self.assistant_version_repo = AssistantVersionRepository(
            InMemoryDocumentCollectionAdapter[AssistantVersionDocument](
                AssistantVersionDocument
            )
        )
        self.autotest_run_repo = AutotestRunRepository(
            InMemoryDocumentCollectionAdapter[AutotestRunDocument](AutotestRunDocument)
        )
        self.flitt_client = FlittClient(
            merchant_id=PlatformIdentifier(FLITT_MERCHANT_ID),
            secret_key=PlatformSecret(FLITT_SECRET_KEY),
            transport=httpx.MockTransport(self.flitt.handle),
        )
        self.payment_gateway = FlittPaymentGatewayAdapter(
            flitt_client=self.flitt_client,
            app_base_url=PublicBaseUrl(APP_BASE_URL),
        )
        self.invoice_description_transformer = InvoiceDescriptionTransformer(resolver)
        self.notice_transformer = BillingNoticeTransformer(resolver)
        authorize = AuthorizeBusinessAccessUseCase(
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
        )
        self.assemble_overview = AssembleBillingOverviewUseCase(
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            usage_event_repo=self.usage_event_repo,
            plan_registry=self.plan_registry,
            exchange_rate_registry=self.exchange_rate_registry,
            localized_text_resolver=resolver,
            wall_clock=wall_clock,
        )
        self.issue_due_invoices = IssueDueInvoicesUseCase(
            invoice_repo=self.invoice_repo,
            plan_registry=self.plan_registry,
            invoice_description_transformer=self.invoice_description_transformer,
            wall_clock=wall_clock,
        )
        self.get_overview = GetBillingOverviewUseCase(
            authorize_business_access=authorize,
            assemble_billing_overview=self.assemble_overview,
        )
        self.start_trial = StartTrialUseCase(
            authorize_business_access=authorize,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            business_repo=self.business_repo,
            plan_registry=self.plan_registry,
            assemble_billing_overview=self.assemble_overview,
            wall_clock=wall_clock,
        )
        self.voice_agent_removals = RecordingVoiceAgentRemoval()
        self.change_plan = ChangePlanUseCase(
            authorize_business_access=authorize,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            business_repo=self.business_repo,
            plan_registry=self.plan_registry,
            payment_gateway=self.payment_gateway,
            assemble_billing_overview=self.assemble_overview,
            wall_clock=wall_clock,
            remove_voice_agent=self.voice_agent_removals,
        )
        self.cancel_subscription = CancelSubscriptionUseCase(
            authorize_business_access=authorize,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            payment_gateway=self.payment_gateway,
            assemble_billing_overview=self.assemble_overview,
            wall_clock=wall_clock,
        )
        self.start_checkout = StartCheckoutUseCase(
            authorize_business_access=authorize,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            payment_order_repo=self.payment_order_repo,
            issue_due_invoices=self.issue_due_invoices,
            payment_gateway=self.payment_gateway,
            app_settings=self.settings,
            wall_clock=wall_clock,
        )
        self.open_subscription = OpenSubscriptionUseCase(
            authorize_business_access=authorize,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            business_repo=self.business_repo,
            plan_registry=self.plan_registry,
            app_settings=self.settings,
            wall_clock=wall_clock,
        )
        self.subscribe = SubscribeOrchestrator(
            open_subscription=self.open_subscription,
            change_plan=self.change_plan,
            start_checkout=self.start_checkout,
        )
        self.process_webhook = ProcessPaymentWebhookUseCase(
            payment_gateway=self.payment_gateway,
            payment_order_repo=self.payment_order_repo,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            plan_registry=self.plan_registry,
            issue_due_invoices=self.issue_due_invoices,
            manager_notifier=self.notifier,
            billing_notice_transformer=self.notice_transformer,
            wall_clock=wall_clock,
        )
        self.end_trials = EndTrialsUseCase(
            business_repo=self.business_repo,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            user_repo=self.user_repo,
            plan_registry=self.plan_registry,
            issue_due_invoices=self.issue_due_invoices,
            manager_notifier=self.notifier,
            billing_notice_transformer=self.notice_transformer,
            wall_clock=wall_clock,
        )
        self.enforce_grace_periods = EnforceGracePeriodsUseCase(
            business_repo=self.business_repo,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            user_repo=self.user_repo,
            plan_registry=self.plan_registry,
            issue_due_invoices=self.issue_due_invoices,
            manager_notifier=self.notifier,
            billing_notice_transformer=self.notice_transformer,
            wall_clock=wall_clock,
        )
        self.check_package_usage = CheckPackageUsageUseCase(
            business_repo=self.business_repo,
            subscription_repo=self.subscription_repo,
            usage_event_repo=self.usage_event_repo,
            package_usage_warning_repo=self.warning_repo,
            user_repo=self.user_repo,
            plan_registry=self.plan_registry,
            exchange_rate_registry=self.exchange_rate_registry,
            manager_notifier=self.notifier,
            billing_notice_transformer=self.notice_transformer,
            wall_clock=wall_clock,
        )
        self.invoice_usage_overage = InvoiceUsageOverageUseCase(
            business_repo=self.business_repo,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            usage_event_repo=self.usage_event_repo,
            user_repo=self.user_repo,
            plan_registry=self.plan_registry,
            exchange_rate_registry=self.exchange_rate_registry,
            invoice_description_transformer=self.invoice_description_transformer,
            manager_notifier=self.notifier,
            billing_notice_transformer=self.notice_transformer,
            wall_clock=wall_clock,
        )
        self.compute_client_cost = ComputeClientCostUseCase(
            business_repo=self.business_repo,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            usage_event_repo=self.usage_event_repo,
            message_repo=self.message_repo,
            exchange_rate_registry=self.exchange_rate_registry,
        )
        authorize_admin = AuthorizePlatformAdminUseCase(user_repo=self.user_repo)
        summarize_client = SummarizeClientUseCase(
            subscription_repo=self.subscription_repo,
            assistant_version_repo=self.assistant_version_repo,
            autotest_run_repo=self.autotest_run_repo,
            handoff_repo=self.handoff_repo,
            unanswered_question_repo=self.question_repo,
            message_repo=self.message_repo,
            usage_event_repo=self.usage_event_repo,
            plan_registry=self.plan_registry,
            compute_client_cost=self.compute_client_cost,
            wall_clock=wall_clock,
        )
        self.summarize_client: SummarizeClientUseCase = summarize_client
        self.list_clients = ListClientsUseCase(
            authorize_platform_admin=authorize_admin,
            business_repo=self.business_repo,
            summarize_client=summarize_client,
            wall_clock=wall_clock,
        )
        self.get_client_health = GetClientHealthUseCase(
            authorize_platform_admin=authorize_admin,
            business_repo=self.business_repo,
            assistant_version_repo=self.assistant_version_repo,
            autotest_run_repo=self.autotest_run_repo,
            invoice_repo=self.invoice_repo,
            payment_order_repo=self.payment_order_repo,
            summarize_client=summarize_client,
        )
        self.open_client_cabinet = OpenClientCabinetUseCase(
            authorize_platform_admin=authorize_admin,
            business_repo=self.business_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
        )

    def add_user(
        self,
        email: str | None = None,
        phone_number: str | None = None,
        locale: str = "en",
        is_platform_admin: bool = False,
        display_name: str | None = None,
    ) -> UserDocument:
        user = UserDocument(
            login_method=LoginMethod.EMAIL if email else LoginMethod.PHONE,
            email=None if email is None else EmailAddress(email),
            phone_number=None
            if phone_number is None
            else E164PhoneNumber(phone_number),
            locale=LanguageTag(locale),
            display_name=None
            if display_name is None
            else UserDisplayName(display_name),
            is_verified=True,
            is_platform_admin=is_platform_admin,
        )
        self.user_repo.save(user)
        return user

    def add_business(
        self,
        owner: UserDocument,
        country: CountryPreset = GEORGIA,
        plan_key: PlanKey = PlanKey.VOICE_AND_CHAT,
        name: str = "Funicular VR",
        staff: list[UserDocument] | None = None,
    ) -> BusinessDocument:
        members: list[BusinessMember] = [
            BusinessMember(user_id=owner.id, role=BusinessMemberRole.OWNER)
        ]
        members.extend(
            BusinessMember(user_id=member.id, role=BusinessMemberRole.STAFF)
            for member in staff or []
        )
        business = BusinessDocument(
            name=BusinessName(name),
            niche_key=NicheKey.ENTERTAINMENT,
            country_code=CountryCode(country.country_code),
            timezone=TimezoneName(country.timezone),
            currency_code=CurrencyCode(country.currency_code),
            languages=[LanguageTag(language) for language in country.languages],
            default_language=LanguageTag(country.languages[0]),
            owner_language=LanguageTag(country.owner_language),
            plan_key=plan_key,
            data_region=DataRegion.EU,
            members=members,
        )
        self.business_repo.save(business)
        return business

    def business(self, business_id: BusinessId) -> BusinessDocument:
        business: BusinessDocument | None = self.business_repo.get(business_id)
        assert business is not None
        return business

    def subscription(self, business_id: BusinessId) -> SubscriptionDocument:
        subscriptions = self.subscription_repo.list_by_business(business_id)
        assert len(subscriptions) == 1
        return subscriptions[0]

    def invoices(self, business_id: BusinessId) -> list[InvoiceDocument]:
        return sorted(
            self.invoice_repo.list_by_business(business_id),
            key=lambda invoice: (invoice.period_start, invoice.kind.value),
        )

    def record_usage(
        self,
        business_id: BusinessId,
        kind: UsageKind,
        quantity: int,
        cost_micro_usd: int = 0,
        conversation_id: ConversationId | None = None,
        occurred_at: Microseconds | None = None,
    ) -> None:
        moment: Microseconds = occurred_at or self.clock.now()
        self.usage_event_repo.append(
            UsageEventDocument(
                business_id=business_id,
                conversation_id=conversation_id,
                kind=kind,
                quantity=UsageQuantity(quantity),
                cost_micro_usd=CostMicroUsd(cost_micro_usd),
                occurred_at=moment,
                created_at=moment,
                updated_at=moment,
            )
        )

    def run_job(self, job: UseCaseContract[JobTick, JobReport], name: str) -> int:
        report: JobReport = job.run(
            JobTick(job_name=JobName(name), scheduled_at=self.clock.now())
        )
        return int(report.processed_count)

    def deliver_flitt_callback(
        self,
        parameters: dict[str, object],
        is_signed: bool = True,
        content_type: str = "application/json",
        encoder: Callable[[dict[str, object]], str] = json.dumps,
    ) -> PaymentWebhookReceipt:
        payload: dict[str, object] = (
            sign_flitt_callback(parameters) if is_signed else parameters
        )
        return self.process_webhook.run(
            PaymentWebhookDelivery(
                body=PaymentWebhookBody(encoder(payload)),
                content_type=PaymentWebhookContentType(content_type),
            )
        )

    def callback_parameters(
        self,
        payment_order: PaymentOrderDocument,
        order_status: str,
        payment_id: int = 900000001,
        amount: int | None = None,
        **extra: object,
    ) -> dict[str, object]:
        return {
            "order_id": str(payment_order.id),
            "merchant_id": int(FLITT_MERCHANT_ID),
            "order_status": order_status,
            "response_status": "success",
            "amount": (int(payment_order.amount_minor) if amount is None else amount),
            "currency": str(payment_order.currency_code),
            "payment_id": payment_id,
            "merchant_data": str(payment_order.id),
            "response_description": "",
            **extra,
        }

    def build_http_client(self) -> TestClient:
        current_user = build_current_user_dependency(
            TokenAuthenticationOperator(self.user_repo)
        )
        http_application = FastAPI()
        install_error_handlers(http_application)
        http_application.include_router(
            build_billing_router(
                get_billing_overview_operator=build_operator(self.get_overview),
                start_trial_operator=build_operator(self.start_trial),
                change_plan_operator=build_operator(self.change_plan),
                cancel_subscription_operator=build_operator(self.cancel_subscription),
                start_checkout_operator=build_operator(self.start_checkout),
                subscribe_operator=PipelineOperator(
                    OrchestratorPipeline(self.subscribe)
                ),
                payment_webhook_operator=build_operator(self.process_webhook),
                current_user=current_user,
            )
        )
        http_application.include_router(
            build_admin_router(
                list_clients_operator=build_operator(self.list_clients),
                get_client_health_operator=build_operator(self.get_client_health),
                open_client_cabinet_operator=build_operator(self.open_client_cabinet),
                current_user=current_user,
            )
        )
        return TestClient(http_application)


def bearer(user: UserDocument) -> dict[str, str]:
    return {"Authorization": f"Bearer {user.id}"}


def describe_notice(testbed: BillingTestbed, notice: BillingNotice) -> str:
    return str(testbed.notice_transformer.transform(notice))


def describe_invoice(
    testbed: BillingTestbed,
    description_input: InvoiceDescriptionInput,
) -> str:
    return str(testbed.invoice_description_transformer.transform(description_input))
