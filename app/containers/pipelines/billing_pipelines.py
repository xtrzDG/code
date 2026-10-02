from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.billing_orchestrators import (
    BillingOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class BillingPipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines of billing and payments: the overview, trials, plans,
    checkout, the payment webhook and the periodic billing jobs.
    """

    billing_orchestrators: BillingOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Billing and payments.
    get_billing_overview_pipeline = orchestrator_pipeline(
        billing_orchestrators.get_billing_overview_orchestrator
    )
    start_trial_pipeline = orchestrator_pipeline(
        billing_orchestrators.start_trial_orchestrator
    )
    change_plan_pipeline = orchestrator_pipeline(
        billing_orchestrators.change_plan_orchestrator
    )
    cancel_subscription_pipeline = orchestrator_pipeline(
        billing_orchestrators.cancel_subscription_orchestrator
    )
    start_checkout_pipeline = orchestrator_pipeline(
        billing_orchestrators.start_checkout_orchestrator
    )
    subscribe_pipeline = orchestrator_pipeline(
        billing_orchestrators.subscribe_orchestrator
    )
    process_payment_webhook_pipeline = orchestrator_pipeline(
        billing_orchestrators.process_payment_webhook_orchestrator
    )

    # --- Periodic jobs of the background worker.
    end_trials_pipeline = orchestrator_pipeline(
        billing_orchestrators.end_trials_orchestrator
    )
    enforce_grace_periods_pipeline = orchestrator_pipeline(
        billing_orchestrators.enforce_grace_periods_orchestrator
    )
    check_package_usage_pipeline = orchestrator_pipeline(
        billing_orchestrators.check_package_usage_orchestrator
    )
    invoice_usage_overage_pipeline = orchestrator_pipeline(
        billing_orchestrators.invoice_usage_overage_orchestrator
    )
