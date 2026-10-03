from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.billing_use_cases import BillingUseCasesContainer
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.billing.subscribe_orchestrator import SubscribeOrchestrator
from app.schemas.dto.billing_cabinet import CheckoutSessionView, SubscribeCommand


class BillingOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of billing and payments: the overview, trials, plans,
    checkout, the payment webhook and the periodic billing jobs.
    """

    billing_use_cases: BillingUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Subscribing with payment now: open, switch plan, checkout.
    subscribe_orchestrator: Factory[
        OrchestratorContract[SubscribeCommand, CheckoutSessionView]
    ] = Factory(
        SubscribeOrchestrator,
        open_subscription=billing_use_cases.open_subscription_use_case,
        change_plan=billing_use_cases.change_plan_use_case,
        start_checkout=billing_use_cases.start_checkout_use_case,
    )

    # --- Billing and payments.
    get_billing_overview_orchestrator = use_case_orchestrator(
        billing_use_cases.get_billing_overview_use_case
    )
    start_trial_orchestrator = use_case_orchestrator(
        billing_use_cases.start_trial_use_case
    )
    change_plan_orchestrator = use_case_orchestrator(
        billing_use_cases.change_plan_use_case
    )
    cancel_subscription_orchestrator = use_case_orchestrator(
        billing_use_cases.cancel_subscription_use_case
    )
    start_checkout_orchestrator = use_case_orchestrator(
        billing_use_cases.start_checkout_use_case
    )
    process_payment_webhook_orchestrator = use_case_orchestrator(
        billing_use_cases.process_payment_webhook_use_case
    )

    # --- Periodic jobs of the background worker.
    end_trials_orchestrator = use_case_orchestrator(
        billing_use_cases.end_trials_use_case
    )
    enforce_grace_periods_orchestrator = use_case_orchestrator(
        billing_use_cases.enforce_grace_periods_use_case
    )
    check_package_usage_orchestrator = use_case_orchestrator(
        billing_use_cases.check_package_usage_use_case
    )
    invoice_usage_overage_orchestrator = use_case_orchestrator(
        billing_use_cases.invoice_usage_overage_use_case
    )
    refresh_exchange_rates_orchestrator = use_case_orchestrator(
        billing_use_cases.refresh_exchange_rates_use_case
    )
