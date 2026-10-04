"""In-memory world of the value context: the operations world plus its own pieces."""

from datetime import datetime

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.facilitators.value.owner_digest_facilitator import OwnerDigestFacilitator
from app.registries.niches.niche_template_registry import NicheTemplateRegistry
from app.registries.niches.niche_value_registry import NicheValueRegistry
from app.repositories.conversation_repositories import MessageRepository
from app.repositories.value_count_repository import ValueCountRepository
from app.repositories.value_repositories import (
    DigestPreferencesRepository,
    ValueReportRepository,
    ValueSettingsRepository,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.value_reports import ValueReportDocument
from app.schemas.domain.value_settings import (
    DigestPreferencesDocument,
    ValueSettingsDocument,
)
from app.transformers.notifications.value_digest_text_transformer import (
    ValueDigestTextTransformer,
)
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.insights.value.compute_value_model_use_case import (
    ComputeValueModelUseCase,
)
from app.use_cases.insights.value.get_business_value_use_case import (
    GetBusinessValueUseCase,
)
from app.use_cases.insights.value.send_value_reports_use_case import (
    SendValueReportsUseCase,
)
from app.use_cases.insights.value.value_counting import ValueSources
from app.use_cases.insights.value.value_estimates import EstimateCatalogs
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.notifications.staff_link_signer import StaffLinkSigner
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.billing.exchange_rate_fixtures import rate_registry
from tests.foundation.access_support import ACCESS_SETTINGS
from tests.notifications.staff_alert_fakes import (
    TEST_ENCRYPTION_KEY,
    preferences_repo,
    push_subscription_repo,
)
from tests.operations.builders import DEFAULT_NOW
from tests.operations.operations_world import OperationsWorld

CABINET_URL: str = "https://cabinet.example.com"


class ValueWorld(OperationsWorld):
    """Everything the value use cases need, wired in memory."""

    def __init__(self, now: datetime = DEFAULT_NOW) -> None:
        super().__init__(now)
        self.message_collection = InMemoryDocumentCollectionAdapter[MessageDocument](
            MessageDocument
        )
        self.message_repo = MessageRepository(self.message_collection)
        self.value_count_repo = ValueCountRepository(
            self.booking_collection, self.message_collection
        )
        self.value_settings_repo = ValueSettingsRepository(
            InMemoryDocumentCollectionAdapter[ValueSettingsDocument](
                ValueSettingsDocument
            )
        )
        self.digest_preferences_repo = DigestPreferencesRepository(
            InMemoryDocumentCollectionAdapter[DigestPreferencesDocument](
                DigestPreferencesDocument
            )
        )
        self.value_report_repo = ValueReportRepository(
            InMemoryDocumentCollectionAdapter[ValueReportDocument](ValueReportDocument)
        )
        self.push_subscription_repo = push_subscription_repo()
        self.notification_preferences_repo = preferences_repo()
        self.exchange_rate_registry: ExchangeRateRegistryContract = rate_registry()
        self.settings: AppSettings = assemble_app_settings(
            {"CABINET_BASE_URL": CABINET_URL}
        )

    def catalogs(self) -> EstimateCatalogs:
        return EstimateCatalogs(
            niche_value_registry=NicheValueRegistry(),
            niche_template_registry=NicheTemplateRegistry(),
            exchange_rate_registry=self.exchange_rate_registry,
            value_settings_repo=self.value_settings_repo,
        )

    def value_sources(self) -> ValueSources:
        return ValueSources(
            conversation_repo=self.conversation_repo,
            message_repo=self.message_repo,
            booking_repo=self.booking_repo,
            lead_repo=self.lead_repo,
            handoff_repo=self.handoff_repo,
            value_count_repo=self.value_count_repo,
        )

    def compute_value(self) -> ComputeValueModelUseCase:
        return ComputeValueModelUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            schedule_exception_repo=self.exception_repo,
            sources=self.value_sources(),
            catalogs=self.catalogs(),
        )

    def authorize(self) -> AuthorizeBusinessAccessUseCase:
        return AuthorizeBusinessAccessUseCase(
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            audit_log_repo=self.audit_repo,
            wall_clock=self.clock.wall_clock,
            session_assurance=SessionAssuranceContext(),
            app_settings=ACCESS_SETTINGS,
        )

    def business_value(self) -> GetBusinessValueUseCase:
        return GetBusinessValueUseCase(
            authorize_business_access=self.authorize(),
            compute_value_model=self.compute_value(),
            wall_clock=self.clock.wall_clock,
        )

    def owner_digests(self) -> OwnerDigestFacilitator:
        return OwnerDigestFacilitator(
            user_repo=self.user_repo,
            digest_preferences_repo=self.digest_preferences_repo,
            push_subscription_repo=self.push_subscription_repo,
            notification_preferences_repo=self.notification_preferences_repo,
            manager_notifier=self.notifier,
            push_queue=self.push_queue,
            link_signer=StaffLinkSigner(TEST_ENCRYPTION_KEY),
            text_transformer=ValueDigestTextTransformer(self.resolver),
            app_settings=self.settings,
            wall_clock=self.clock.wall_clock,
        )

    def send_value_reports(self) -> SendValueReportsUseCase:
        return SendValueReportsUseCase(
            business_repo=self.business_repo,
            value_report_repo=self.value_report_repo,
            digest_preferences_repo=self.digest_preferences_repo,
            compute_value_model=self.compute_value(),
            owner_digests=self.owner_digests(),
            wall_clock=self.clock.wall_clock,
        )
