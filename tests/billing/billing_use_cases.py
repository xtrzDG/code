"""The billing testbed's billing, worker job and admin use cases, wired."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.registries import PlanRegistryContract
from app.orchestrators.billing.subscribe_orchestrator import SubscribeOrchestrator
from app.use_cases.admin.authorize_platform_admin_use_case import (
    AuthorizePlatformAdminUseCase,
)
from app.use_cases.admin.get_client_health_use_case import GetClientHealthUseCase
from app.use_cases.admin.list_clients_use_case import ListClientsUseCase
from app.use_cases.admin.open_client_cabinet_use_case import OpenClientCabinetUseCase
from app.use_cases.admin.summarize_client_use_case import SummarizeClientUseCase
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.billing.assemble_billing_overview_use_case import (
    AssembleBillingOverviewUseCase,
)
from app.use_cases.billing.cancel_subscription_use_case import CancelSubscriptionUseCase
from app.use_cases.billing.change_plan_use_case import ChangePlanUseCase
from app.use_cases.billing.check_package_usage_use_case import CheckPackageUsageUseCase
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
from tests.billing.billing_fakes import RecordingVoiceAgentRemoval
from tests.billing.billing_infrastructure import BillingInfrastructure


class BillingUseCases(BillingInfrastructure):
    """Every billing and admin use case over the infrastructure."""

    def __init__(
        self,
        plan_registry: PlanRegistryContract | None = None,
        exchange_rate_registry: ExchangeRateRegistryContract | None = None,
    ) -> None:
        super().__init__(plan_registry, exchange_rate_registry)
        resolver = LocalizedTextResolver()
        wall_clock: WallClock[Microseconds] = self.clock.wall_clock
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
