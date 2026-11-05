from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.platform_ops_use_cases import PlatformOpsUseCasesContainer
from app.containers.use_cases.spend_guard_use_cases import SpendGuardUseCasesContainer


class SpendGuardOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of the spend guard's endpoints (one use case each): the
    generic API limits, the website-chat origin check and its list, and the
    admin's spend tile and a client's limits.
    """

    spend_guard_use_cases: SpendGuardUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    platform_ops_use_cases: PlatformOpsUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    admit_api_request_orchestrator = use_case_orchestrator(
        spend_guard_use_cases.admit_api_request_use_case
    )
    check_widget_origin_orchestrator = use_case_orchestrator(
        spend_guard_use_cases.check_widget_origin_use_case
    )
    get_widget_allowed_origins_orchestrator = use_case_orchestrator(
        spend_guard_use_cases.get_widget_allowed_origins_use_case
    )
    save_widget_allowed_origins_orchestrator = use_case_orchestrator(
        spend_guard_use_cases.save_widget_allowed_origins_use_case
    )
    get_platform_spend_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.get_platform_spend_use_case
    )
    set_business_spend_limits_orchestrator = use_case_orchestrator(
        platform_ops_use_cases.set_business_spend_limits_use_case
    )
    # The platform's brakes and the daily payment reconciliation (1230).
    get_platform_pause_orchestrator = use_case_orchestrator(
        spend_guard_use_cases.get_platform_pause_use_case
    )
    set_platform_pause_orchestrator = use_case_orchestrator(
        spend_guard_use_cases.set_platform_pause_use_case
    )
    reconcile_payments_orchestrator = use_case_orchestrator(
        spend_guard_use_cases.reconcile_payments_use_case
    )
    get_payment_reconciliation_orchestrator = use_case_orchestrator(
        spend_guard_use_cases.get_payment_reconciliation_use_case
    )
    # The feature flags of staged rollouts (1260).
    list_feature_flags_orchestrator = use_case_orchestrator(
        spend_guard_use_cases.list_feature_flags_use_case
    )
    set_feature_flag_orchestrator = use_case_orchestrator(
        spend_guard_use_cases.set_feature_flag_use_case
    )
    check_feature_flag_orchestrator = use_case_orchestrator(
        spend_guard_use_cases.check_feature_flag_use_case
    )
