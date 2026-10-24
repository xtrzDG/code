from dependency_injector.providers import Factory, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.payments.payment_dependencies import PaymentDependencies
from app.containers.payments.payment_root import PaymentRoot
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.billing_use_cases import BillingUseCasesContainer
from app.containers.utilities import UtilitiesContainer


def payment_root_provider(
    *,
    adapters: AdaptersContainer,
    config: ConfigContainer,
    facilitators: FacilitatorsContainer,
    registries: RegistriesContainer,
    repositories: RepositoriesContainer,
    time_provider: TimeProviderContainer,
    transformers: TransformersContainer,
    utilities: UtilitiesContainer,
    account_use_cases: AccountUseCasesContainer,
    billing_use_cases: BillingUseCasesContainer,
) -> Singleton[PaymentRoot]:
    """
    The payments context's one root (R17-PAYMENTS-REGIONAL, migration
    1214), its dependencies taken from the graph: the single seam between
    the providers and the typed root (app/containers/payments/, ADR 0010;
    a missing or misspelt field fails
    test_every_provider_of_the_container_resolves).
    """

    return Singleton(
        PaymentRoot,
        dependencies=Factory(
            PaymentDependencies,
            authorize_business_access=account_use_cases.authorize_business_access_use_case,
            issue_due_invoices=billing_use_cases.issue_due_invoices_use_case,
            subscription_repo=repositories.subscription_repo,
            invoice_repo=repositories.invoice_repo,
            payment_order_repo=repositories.payment_order_repo,
            payment_retry_repo=repositories.payment_retry_repo,
            business_repo=repositories.business_repo,
            brand_repo=repositories.brand_repo,
            user_repo=repositories.user_repo,
            payment_gateway=adapters.payment_gateway,
            plan_registry=registries.plan_registry,
            invoice_issuing=facilitators.invoice_issuing_facilitator,
            manager_notifier=facilitators.manager_notification_facilitator,
            link_signer=facilitators.staff_link_signer,
            referral_earnings=facilitators.referral_earnings,
            product_events=facilitators.product_events,
            secret_cipher=adapters.secret_cipher,
            localized_text_resolver=utilities.localized_text_resolver,
            billing_notice_transformer=transformers.billing_notice_transformer,
            invoice_description_transformer=transformers.invoice_description_transformer,
            app_settings=config.app_settings,
            wall_clock=time_provider.microsecond_wall_clock,
        ),
    )
