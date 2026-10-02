from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.billing_pipelines import BillingPipelinesContainer
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class BillingOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of billing and payments: the overview, trials, plans,
    checkout, the payment webhook and the periodic billing jobs.
    """

    billing_pipelines: BillingPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # Operators run inside the storage scope of the business they serve.
    storage_scope = utilities.storage_scope

    # --- Billing and payments.
    get_billing_overview_operator = pipeline_operator(
        billing_pipelines.get_billing_overview_pipeline, storage_scope
    )
    start_trial_operator = pipeline_operator(
        billing_pipelines.start_trial_pipeline, storage_scope
    )
    change_plan_operator = pipeline_operator(
        billing_pipelines.change_plan_pipeline, storage_scope
    )
    cancel_subscription_operator = pipeline_operator(
        billing_pipelines.cancel_subscription_pipeline, storage_scope
    )
    start_checkout_operator = pipeline_operator(
        billing_pipelines.start_checkout_pipeline, storage_scope
    )
    subscribe_operator = pipeline_operator(
        billing_pipelines.subscribe_pipeline, storage_scope
    )
    process_payment_webhook_operator = pipeline_operator(
        billing_pipelines.process_payment_webhook_pipeline, storage_scope
    )

    # --- Periodic jobs of the background worker.
    end_trials_operator = pipeline_operator(
        billing_pipelines.end_trials_pipeline, storage_scope
    )
    enforce_grace_periods_operator = pipeline_operator(
        billing_pipelines.enforce_grace_periods_pipeline, storage_scope
    )
    check_package_usage_operator = pipeline_operator(
        billing_pipelines.check_package_usage_pipeline, storage_scope
    )
    invoice_usage_overage_operator = pipeline_operator(
        billing_pipelines.invoice_usage_overage_pipeline, storage_scope
    )
