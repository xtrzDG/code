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
