"""The billing testbed's billing, worker job and admin use cases, wired."""

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.registries import PlanRegistryContract
from app.orchestrators.billing.subscribe_orchestrator import SubscribeOrchestrator
from app.repositories.client_standing_repository import ClientStandingRepository
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.client_standings import ClientStandingDocument
from app.use_cases.admin.get_client_health_use_case import GetClientHealthUseCase
from app.use_cases.admin.list_clients_use_case import ListClientsUseCase
from app.use_cases.admin.open_client_cabinet_use_case import OpenClientCabinetUseCase
from app.use_cases.admin.refresh_client_standings_use_case import (
    RefreshClientStandingsUseCase,
)
from app.use_cases.admin.summarize_client_use_case import SummarizeClientUseCase
from app.use_cases.billing.assemble_billing_overview_use_case import (
    AssembleBillingOverviewUseCase,
)
from app.use_cases.billing.cancel_subscription_use_case import CancelSubscriptionUseCase
from app.use_cases.billing.change_plan_use_case import ChangePlanUseCase
from app.use_cases.billing.check_package_usage_use_case import CheckPackageUsageUseCase
from app.use_cases.billing.choose_setup_option_use_case import (
    ChooseSetupOptionUseCase,
)
from app.use_cases.billing.compute_client_cost_use_case import ComputeClientCostUseCase
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
from app.use_cases.billing.issue_due_invoices_use_case import IssueDueInvoicesUseCase
from app.use_cases.billing.open_subscription_use_case import OpenSubscriptionUseCase
from app.use_cases.billing.payment_webhook.process_payment_webhook_use_case import (
    ProcessPaymentWebhookUseCase,
)
from app.use_cases.billing.start_checkout_use_case import StartCheckoutUseCase
from app.use_cases.billing.start_trial_use_case import StartTrialUseCase
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.analytics.recording_product_events import RecordingProductEvents
from tests.billing.billing_fakes import RecordingVoiceAgentRemoval
from tests.billing.billing_infrastructure import BillingInfrastructure
from tests.foundation.access_support import (
    ACCESS_SETTINGS,
    AllowStepUp,
    AuthorizeFlaggedAdmin,
)
from tests.foundation.support_access_builders import (
    RecordingStaffAlerts,
    build_authorize_business_access,
    in_memory_grant_repo,
    in_memory_platform_admins,
)


class BillingUseCases(BillingInfrastructure):
    """Every billing and admin use case over the infrastructure."""

    def __init__(
        self,
        plan_registry: PlanRegistryContract | None = None,
        exchange_rate_registry: ExchangeRateRegistryContract | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        super().__init__(plan_registry, exchange_rate_registry, settings)
        self.product_events = RecordingProductEvents()
        resolver = LocalizedTextResolver()
        wall_clock: WallClock[Microseconds] = self.clock.wall_clock
        authorize = build_authorize_business_access(
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
            session_assurance=SessionAssuranceContext(),
            app_settings=ACCESS_SETTINGS,
        )
        self.authorize = authorize
        self.assemble_overview = AssembleBillingOverviewUseCase(
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            usage_event_repo=self.usage_event_repo,
            onboarding_request_repo=self.onboarding_request_repo,
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
            invoice_issuing=self.invoicing.invoice_issuing,
            invoice_line_texts_transformer=self.invoice_line_texts_transformer,
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
            product_events=self.product_events,
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
            product_events=self.product_events,
        )
        self.cancel_subscription = CancelSubscriptionUseCase(
            authorize_business_access=authorize,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            payment_gateway=self.payment_gateway,
            assemble_billing_overview=self.assemble_overview,
            wall_clock=wall_clock,
            product_events=self.product_events,
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
            invoice_issuing=self.invoicing.invoice_issuing,
        )
        self.choose_setup_option = ChooseSetupOptionUseCase(
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            onboarding_request_repo=self.onboarding_request_repo,
            manager_notifier=self.notifier,
            app_settings=self.settings,
            wall_clock=wall_clock,
        )
        self.open_subscription = OpenSubscriptionUseCase(
            authorize_business_access=authorize,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            business_repo=self.business_repo,
            plan_registry=self.plan_registry,
            choose_setup_option=self.choose_setup_option,
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
            product_events=self.product_events,
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
            product_events=self.product_events,
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
            invoice_issuing=self.invoicing.invoice_issuing,
            invoice_line_texts_transformer=self.invoice_line_texts_transformer,
        )
        self.compute_client_cost = ComputeClientCostUseCase(
            business_repo=self.business_repo,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            usage_event_repo=self.usage_event_repo,
            message_repo=self.message_repo,
            exchange_rate_registry=self.exchange_rate_registry,
        )
        authorize_admin = AuthorizeFlaggedAdmin(self.user_repo)
        summarize_client = SummarizeClientUseCase(
            subscription_repo=self.subscription_repo,
            assistant_version_repo=self.assistant_version_repo,
            handoff_repo=self.handoff_repo,
            unanswered_question_repo=self.question_repo,
            message_repo=self.message_repo,
            usage_event_repo=self.usage_event_repo,
            onboarding_request_repo=self.onboarding_request_repo,
            plan_registry=self.plan_registry,
            compute_client_cost=self.compute_client_cost,
            wall_clock=wall_clock,
        )
        self.summarize_client: SummarizeClientUseCase = summarize_client
        self.client_standing_repo = ClientStandingRepository(
            InMemoryDocumentCollectionAdapter(ClientStandingDocument)
        )
        self.refresh_client_standings = RefreshClientStandingsUseCase(
            self.business_repo, summarize_client, self.client_standing_repo, wall_clock
        )
        self.list_clients = ListClientsUseCase(
            authorize_platform_admin=authorize_admin,
            client_standing_repo=self.client_standing_repo,
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
        self.support_grants = in_memory_grant_repo()
        self.staff_alerts = RecordingStaffAlerts()
        self.open_client_cabinet = OpenClientCabinetUseCase(
            authorize_platform_admin=authorize_admin,
            platform_admins=in_memory_platform_admins(wall_clock),
            business_repo=self.business_repo,
            grant_repo=self.support_grants,
            audit_log_repo=self.audit_log_repo,
            staff_alerts=self.staff_alerts,
            localized_text_resolver=LocalizedTextResolver(),
            wall_clock=wall_clock,
            step_up=AllowStepUp(),
        )
