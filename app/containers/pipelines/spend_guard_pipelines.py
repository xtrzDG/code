from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.spend_guard_orchestrators import (
    SpendGuardOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class SpendGuardPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the spend guard's endpoints."""

    spend_guard: SpendGuardOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    admit_api_request_pipeline = orchestrator_pipeline(
        spend_guard.admit_api_request_orchestrator
    )
    check_widget_origin_pipeline = orchestrator_pipeline(
        spend_guard.check_widget_origin_orchestrator
    )
    get_widget_allowed_origins_pipeline = orchestrator_pipeline(
        spend_guard.get_widget_allowed_origins_orchestrator
    )
    save_widget_allowed_origins_pipeline = orchestrator_pipeline(
        spend_guard.save_widget_allowed_origins_orchestrator
    )
    get_platform_spend_pipeline = orchestrator_pipeline(
        spend_guard.get_platform_spend_orchestrator
    )
    set_business_spend_limits_pipeline = orchestrator_pipeline(
        spend_guard.set_business_spend_limits_orchestrator
    )
    # The platform's brakes and the daily payment reconciliation (1230).
    get_platform_pause_pipeline = orchestrator_pipeline(
        spend_guard.get_platform_pause_orchestrator
    )
    set_platform_pause_pipeline = orchestrator_pipeline(
        spend_guard.set_platform_pause_orchestrator
    )
    reconcile_payments_pipeline = orchestrator_pipeline(
        spend_guard.reconcile_payments_orchestrator
    )
    get_payment_reconciliation_pipeline = orchestrator_pipeline(
        spend_guard.get_payment_reconciliation_orchestrator
    )
    # The feature flags of staged rollouts (1260).
    list_feature_flags_pipeline = orchestrator_pipeline(
        spend_guard.list_feature_flags_orchestrator
    )
    set_feature_flag_pipeline = orchestrator_pipeline(
        spend_guard.set_feature_flag_orchestrator
    )
    check_feature_flag_pipeline = orchestrator_pipeline(
        spend_guard.check_feature_flag_orchestrator
    )
