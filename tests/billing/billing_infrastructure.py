"""The billing testbed's base: clock, Flitt sandbox, registries and repositories."""

import httpx

from app.adapters.payments.flitt_payment_gateway_adapter import (
    FlittPaymentGatewayAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.clients.flitt.flitt_client import FlittClient
from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.registries import PlanRegistryContract
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
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.domain.billing import (
    InvoiceDocument,
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.domain.package_usage import PackageUsageWarningDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.domain.users import UserDocument
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from app.transformers.billing.billing_notice_transformer import BillingNoticeTransformer
from app.transformers.billing.invoice_description_transformer import (
    InvoiceDescriptionTransformer,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.billing.billing_fakes import AdjustableClock, RecordingNotifier
from tests.billing.billing_settings import (
    APP_BASE_URL,
    FLITT_MERCHANT_ID,
    FLITT_SECRET_KEY,
    build_settings,
)
from tests.billing.exchange_rate_fixtures import rate_registry
from tests.billing.flitt_sandbox import FlittSandbox


class BillingInfrastructure:
    """In-memory repositories, the Flitt gateway over the sandbox and transformers."""

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
            exchange_rate_registry or rate_registry()
        )
        resolver = LocalizedTextResolver()
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
