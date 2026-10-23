from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.billing_use_cases import BillingUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.facilitators.billing.dunning_notice_facilitator import (
    DunningNoticeFacilitator,
)
from app.registries.billing.payment_provider_registry import PaymentProviderRegistry
from app.schemas.constants.payments import PaymentWebhookOutcome
from app.schemas.dto.billing_cabinet import CheckoutSessionView, StartCheckoutCommand
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.payment_methods import (
    CardSetupSessionView,
    PaymentMethodQuery,
    PaymentMethodView,
    StartCardSetupCommand,
)
from app.schemas.dto.payment_webhooks import PaymentStatusChange
from app.schemas.dto.payments import PaymentWebhookDelivery, PaymentWebhookReceipt
from app.use_cases.billing.card_on_file.get_payment_method_use_case import (
    GetPaymentMethodUseCase,
)
from app.use_cases.billing.card_on_file.retry_failed_payments_use_case import (
    RetryFailedPaymentsUseCase,
)
from app.use_cases.billing.card_on_file.start_card_setup_use_case import (
    StartCardSetupUseCase,
)
from app.use_cases.billing.payment_webhook.apply_payment_status_use_case import (
    ApplyPaymentStatusUseCase,
)
from app.use_cases.billing.payment_webhook.process_payment_webhook_use_case import (
    ProcessPaymentWebhookUseCase,
)
from app.use_cases.billing.start_checkout_use_case import StartCheckoutUseCase


class PaymentUseCasesContainer(containers.DeclarativeContainer):
    """
    Payments (R17-PAYMENTS-REGIONAL, migration 1214): the provider of each
    country (Flitt or Stripe), checkout, the payment webhooks of both
    providers, the card on file ("Save card", "Update card") and the
    retries of declined automatic charges with the owners' notices.
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
    billing_use_cases: BillingUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    payment_provider_registry: Singleton[PaymentProviderRegistry] = Singleton(
        PaymentProviderRegistry,
        payment_settings=config.app_settings.provided.payments,
    )
    dunning_notice_facilitator: Singleton[DunningNoticeFacilitator] = Singleton(
        DunningNoticeFacilitator,
        user_repo=repositories.user_repo,
        manager_notifier=facilitators.manager_notification_facilitator,
        link_signer=facilitators.staff_link_signer,
        localized_text_resolver=utilities.localized_text_resolver,
        app_settings=config.app_settings,
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
        issue_due_invoices=billing_use_cases.issue_due_invoices_use_case,
        payment_gateway=adapters.payment_gateway,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
        invoice_issuing=facilitators.invoice_issuing_facilitator,
        payment_provider_registry=payment_provider_registry,
    )
    apply_payment_status_use_case: Factory[
        UseCaseContract[PaymentStatusChange, PaymentWebhookOutcome]
    ] = Factory(
        ApplyPaymentStatusUseCase,
        payment_gateway=adapters.payment_gateway,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        plan_registry=registries.plan_registry,
        issue_due_invoices=billing_use_cases.issue_due_invoices_use_case,
        manager_notifier=facilitators.manager_notification_facilitator,
        billing_notice_transformer=transformers.billing_notice_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
        referral_earnings=facilitators.referral_earnings,
        payment_retry_repo=repositories.payment_retry_repo,
        payment_order_repo=repositories.payment_order_repo,
    )
    process_payment_webhook_use_case: Factory[
        UseCaseContract[PaymentWebhookDelivery, PaymentWebhookReceipt]
    ] = Factory(
        ProcessPaymentWebhookUseCase,
        payment_gateway=adapters.payment_gateway,
        payment_order_repo=repositories.payment_order_repo,
        subscription_repo=repositories.subscription_repo,
        business_repo=repositories.business_repo,
        apply_payment_status=apply_payment_status_use_case,
        secret_cipher=adapters.secret_cipher,
        wall_clock=time_provider.microsecond_wall_clock,
        product_events=facilitators.product_events,
    )
    get_payment_method_use_case: Factory[
        UseCaseContract[PaymentMethodQuery, PaymentMethodView]
    ] = Factory(
        GetPaymentMethodUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        payment_retry_repo=repositories.payment_retry_repo,
        plan_registry=registries.plan_registry,
        payment_provider_registry=payment_provider_registry,
        wall_clock=time_provider.microsecond_wall_clock,
        invoice_issuing=facilitators.invoice_issuing_facilitator,
        brand_repo=repositories.brand_repo,
        business_repo=repositories.business_repo,
    )
    start_card_setup_use_case: Factory[
        UseCaseContract[StartCardSetupCommand, CardSetupSessionView]
    ] = Factory(
        StartCardSetupUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        payment_order_repo=repositories.payment_order_repo,
        payment_gateway=adapters.payment_gateway,
        payment_provider_registry=payment_provider_registry,
        invoice_issuing=facilitators.invoice_issuing_facilitator,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
        issue_due_invoices=billing_use_cases.issue_due_invoices_use_case,
        plan_registry=registries.plan_registry,
        invoice_description_transformer=transformers.invoice_description_transformer,
    )
    retry_failed_payments_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            RetryFailedPaymentsUseCase,
            business_repo=repositories.business_repo,
            subscription_repo=repositories.subscription_repo,
            invoice_repo=repositories.invoice_repo,
            payment_order_repo=repositories.payment_order_repo,
            payment_retry_repo=repositories.payment_retry_repo,
            plan_registry=registries.plan_registry,
            payment_gateway=adapters.payment_gateway,
            secret_cipher=adapters.secret_cipher,
            dunning_notices=dunning_notice_facilitator,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
