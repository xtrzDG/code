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
from app.facilitators.billing.owner_win_back_facilitator import (
    OwnerWinBackFacilitator,
)
from app.registries.billing.subscription_lifecycle_policy_registry import (
    SubscriptionLifecyclePolicyRegistry,
)
from app.schemas.dto.billing_cabinet import BillingOverview, BillingOverviewSource
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.subscription_lifecycle import (
    AcceptRetentionOfferCommand,
    PauseSubscriptionCommand,
    ResumeSubscriptionCommand,
    SubscriptionLifecycleQuery,
    SubscriptionLifecycleView,
)
from app.use_cases.billing.lifecycle.accept_retention_offer_use_case import (
    AcceptRetentionOfferUseCase,
)
from app.use_cases.billing.lifecycle.assemble_subscription_lifecycle_use_case import (
    AssembleSubscriptionLifecycleUseCase,
)
from app.use_cases.billing.lifecycle.get_subscription_lifecycle_use_case import (
    GetSubscriptionLifecycleUseCase,
)
from app.use_cases.billing.lifecycle.pause_subscription_use_case import (
    PauseSubscriptionUseCase,
)
from app.use_cases.billing.lifecycle.resume_subscription_use_case import (
    ResumeSubscriptionUseCase,
)
from app.use_cases.billing.lifecycle.run_subscription_pauses_use_case import (
    RunSubscriptionPausesUseCase,
)
from app.use_cases.billing.lifecycle.send_win_back_messages_use_case import (
    SendWinBackMessagesUseCase,
)


class SubscriptionLifecycleUseCasesContainer(containers.DeclarativeContainer):
    """
    The subscription lifecycle (R14, migration 1161): the cancel dialog's
    offers, the seasonal pause and its job, and the win-back messages, on
    top of the billing use cases they hand plan changes and invoices to.
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

    lifecycle_policy_registry: Singleton[SubscriptionLifecyclePolicyRegistry] = (
        Singleton(SubscriptionLifecyclePolicyRegistry)
    )
    owner_win_back_facilitator: Singleton[OwnerWinBackFacilitator] = Singleton(
        OwnerWinBackFacilitator,
        user_repo=repositories.user_repo,
        manager_notifier=facilitators.manager_notification_facilitator,
        link_signer=facilitators.staff_link_signer,
        localized_text_resolver=utilities.localized_text_resolver,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    assemble_subscription_lifecycle_use_case: Factory[
        UseCaseContract[BillingOverviewSource, SubscriptionLifecycleView]
    ] = Factory(
        AssembleSubscriptionLifecycleUseCase,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        subscription_event_repo=repositories.subscription_event_repo,
        billing_credit_repo=repositories.billing_credit_repo,
        plan_registry=registries.plan_registry,
        lifecycle_policy_registry=lifecycle_policy_registry,
        localized_text_resolver=utilities.localized_text_resolver,
        app_settings=config.app_settings,
    )
    get_subscription_lifecycle_use_case: Factory[
        UseCaseContract[SubscriptionLifecycleQuery, SubscriptionLifecycleView]
    ] = Factory(
        GetSubscriptionLifecycleUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        assemble_subscription_lifecycle=assemble_subscription_lifecycle_use_case,
    )
    pause_subscription_use_case: Factory[
        UseCaseContract[PauseSubscriptionCommand, BillingOverview]
    ] = Factory(
        PauseSubscriptionUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        subscription_event_repo=repositories.subscription_event_repo,
        payment_gateway=adapters.payment_gateway,
        lifecycle_policy_registry=lifecycle_policy_registry,
        app_settings=config.app_settings,
        assemble_billing_overview=billing_use_cases.assemble_billing_overview_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    resume_subscription_use_case: Factory[
        UseCaseContract[ResumeSubscriptionCommand, BillingOverview]
    ] = Factory(
        ResumeSubscriptionUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        business_repo=repositories.business_repo,
        subscription_event_repo=repositories.subscription_event_repo,
        payment_gateway=adapters.payment_gateway,
        assemble_billing_overview=billing_use_cases.assemble_billing_overview_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    accept_retention_offer_use_case: Factory[
        UseCaseContract[AcceptRetentionOfferCommand, BillingOverview]
    ] = Factory(
        AcceptRetentionOfferUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        assemble_subscription_lifecycle=assemble_subscription_lifecycle_use_case,
        pause_subscription=pause_subscription_use_case,
        change_plan=billing_use_cases.change_plan_use_case,
        assemble_billing_overview=billing_use_cases.assemble_billing_overview_use_case,
        subscription_repo=repositories.subscription_repo,
        billing_credit_repo=repositories.billing_credit_repo,
        subscription_event_repo=repositories.subscription_event_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    run_subscription_pauses_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            RunSubscriptionPausesUseCase,
            business_repo=repositories.business_repo,
            subscription_repo=repositories.subscription_repo,
            invoice_repo=repositories.invoice_repo,
            subscription_event_repo=repositories.subscription_event_repo,
            user_repo=repositories.user_repo,
            issue_due_invoices=billing_use_cases.issue_due_invoices_use_case,
            lifecycle_policy_registry=lifecycle_policy_registry,
            manager_notifier=facilitators.manager_notification_facilitator,
            billing_notice_transformer=transformers.billing_notice_transformer,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    send_win_back_messages_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            SendWinBackMessagesUseCase,
            business_repo=repositories.business_repo,
            subscription_repo=repositories.subscription_repo,
            subscription_event_repo=repositories.subscription_event_repo,
            conversation_repo=repositories.conversation_repo,
            lifecycle_policy_registry=lifecycle_policy_registry,
            owner_win_back=owner_win_back_facilitator,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
