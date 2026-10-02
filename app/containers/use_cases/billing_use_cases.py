from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.voice_use_cases import VoiceUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.dto.billing_cabinet import (
    BillingOverview,
    BillingOverviewQuery,
    BillingOverviewSource,
    CancelSubscriptionCommand,
    ChangePlanCommand,
    CheckoutSessionView,
    StartCheckoutCommand,
    StartTrialCommand,
    SubscribeCommand,
    SubscriptionOpening,
)
from app.schemas.dto.billing_ledger import (
    ClientCostQuery,
    ClientCostReport,
    DueInvoicesRequest,
)
from app.schemas.dto.jobs import (
    JobReport,
    JobTick,
)
from app.schemas.dto.payments import (
    PaymentWebhookDelivery,
    PaymentWebhookReceipt,
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
from app.use_cases.billing.open_subscription_use_case import (
    OpenSubscriptionUseCase,
)
from app.use_cases.billing.payment_webhook.process_payment_webhook_use_case import (
    ProcessPaymentWebhookUseCase,
)
from app.use_cases.billing.start_checkout_use_case import StartCheckoutUseCase
from app.use_cases.billing.start_trial_use_case import StartTrialUseCase


class BillingUseCasesContainer(containers.DeclarativeContainer):
    """
    Billing: subscriptions, invoices, checkout, the payment webhook, the
    periodic billing jobs and the cost of a client.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    voice_use_cases: VoiceUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    issue_due_invoices_use_case: Factory[
        UseCaseContract[DueInvoicesRequest, list[InvoiceDocument]]
    ] = Factory(
        IssueDueInvoicesUseCase,
        invoice_repo=repositories.invoice_repo,
        plan_registry=registries.plan_registry,
        invoice_description_transformer=transformers.invoice_description_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    assemble_billing_overview_use_case: Factory[
        UseCaseContract[BillingOverviewSource, BillingOverview]
    ] = Factory(
        AssembleBillingOverviewUseCase,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        usage_event_repo=repositories.usage_event_repo,
        plan_registry=registries.plan_registry,
        exchange_rate_registry=registries.exchange_rate_registry,
        localized_text_resolver=utilities.localized_text_resolver,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_billing_overview_use_case: Factory[
        UseCaseContract[BillingOverviewQuery, BillingOverview]
    ] = Factory(
        GetBillingOverviewUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        assemble_billing_overview=assemble_billing_overview_use_case,
    )
    start_trial_use_case: Factory[
        UseCaseContract[StartTrialCommand, BillingOverview]
    ] = Factory(
        StartTrialUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        business_repo=repositories.business_repo,
        plan_registry=registries.plan_registry,
        assemble_billing_overview=assemble_billing_overview_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    change_plan_use_case: Factory[
        UseCaseContract[ChangePlanCommand, BillingOverview]
    ] = Factory(
        ChangePlanUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        business_repo=repositories.business_repo,
        plan_registry=registries.plan_registry,
        payment_gateway=adapters.payment_gateway,
        assemble_billing_overview=assemble_billing_overview_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
        remove_voice_agent=voice_use_cases.remove_voice_agent_use_case,
    )
    cancel_subscription_use_case: Factory[
        UseCaseContract[CancelSubscriptionCommand, BillingOverview]
    ] = Factory(
        CancelSubscriptionUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        payment_gateway=adapters.payment_gateway,
        assemble_billing_overview=assemble_billing_overview_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    start_checkout_use_case: Factory[
        UseCaseContract[StartCheckoutCommand, CheckoutSessionView]
    ] = Factory(
        StartCheckoutUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        payment_order_repo=repositories.payment_order_repo,
        issue_due_invoices=issue_due_invoices_use_case,
        payment_gateway=adapters.payment_gateway,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    open_subscription_use_case: Factory[
        UseCaseContract[SubscribeCommand, SubscriptionOpening]
    ] = Factory(
        OpenSubscriptionUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        business_repo=repositories.business_repo,
        plan_registry=registries.plan_registry,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    process_payment_webhook_use_case: Factory[
        UseCaseContract[PaymentWebhookDelivery, PaymentWebhookReceipt]
    ] = Factory(
        ProcessPaymentWebhookUseCase,
        payment_gateway=adapters.payment_gateway,
        payment_order_repo=repositories.payment_order_repo,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        plan_registry=registries.plan_registry,
        issue_due_invoices=issue_due_invoices_use_case,
        manager_notifier=facilitators.manager_notification_facilitator,
        billing_notice_transformer=transformers.billing_notice_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    end_trials_use_case: Factory[UseCaseContract[JobTick, JobReport]] = Factory(
        EndTrialsUseCase,
        business_repo=repositories.business_repo,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        user_repo=repositories.user_repo,
        plan_registry=registries.plan_registry,
        issue_due_invoices=issue_due_invoices_use_case,
        manager_notifier=facilitators.manager_notification_facilitator,
        billing_notice_transformer=transformers.billing_notice_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    enforce_grace_periods_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            EnforceGracePeriodsUseCase,
            business_repo=repositories.business_repo,
            subscription_repo=repositories.subscription_repo,
            invoice_repo=repositories.invoice_repo,
            user_repo=repositories.user_repo,
            plan_registry=registries.plan_registry,
            issue_due_invoices=issue_due_invoices_use_case,
            manager_notifier=facilitators.manager_notification_facilitator,
            billing_notice_transformer=transformers.billing_notice_transformer,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    check_package_usage_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            CheckPackageUsageUseCase,
            business_repo=repositories.business_repo,
            subscription_repo=repositories.subscription_repo,
            usage_event_repo=repositories.usage_event_repo,
            package_usage_warning_repo=repositories.package_usage_warning_repo,
            user_repo=repositories.user_repo,
            plan_registry=registries.plan_registry,
            exchange_rate_registry=registries.exchange_rate_registry,
            manager_notifier=facilitators.manager_notification_facilitator,
            billing_notice_transformer=transformers.billing_notice_transformer,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    invoice_usage_overage_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            InvoiceUsageOverageUseCase,
            business_repo=repositories.business_repo,
            subscription_repo=repositories.subscription_repo,
            invoice_repo=repositories.invoice_repo,
            usage_event_repo=repositories.usage_event_repo,
            user_repo=repositories.user_repo,
            plan_registry=registries.plan_registry,
            exchange_rate_registry=registries.exchange_rate_registry,
            invoice_description_transformer=(
                transformers.invoice_description_transformer
            ),
            manager_notifier=facilitators.manager_notification_facilitator,
            billing_notice_transformer=transformers.billing_notice_transformer,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    compute_client_cost_use_case: Factory[
        UseCaseContract[ClientCostQuery, ClientCostReport]
    ] = Factory(
        ComputeClientCostUseCase,
        business_repo=repositories.business_repo,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        usage_event_repo=repositories.usage_event_repo,
        message_repo=repositories.message_repo,
        exchange_rate_registry=registries.exchange_rate_registry,
    )
