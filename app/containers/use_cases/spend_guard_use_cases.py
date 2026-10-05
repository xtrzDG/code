from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory, Singleton

from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.facilitators.spend_guard.spend_limit_notice_facilitator import (
    SpendLimitNoticeFacilitator,
)
from app.use_cases.spend_guard.admit_api_request_use_case import (
    AdmitApiRequestUseCase,
)
from app.use_cases.spend_guard.admit_owner_action_use_case import (
    AdmitOwnerActionUseCase,
)
from app.use_cases.spend_guard.check_business_spend_use_case import (
    CheckBusinessSpendUseCase,
)


def admit_owner_action_factory(
    registries: RegistriesContainer, time_provider: TimeProviderContainer
) -> Factory[AdmitOwnerActionUseCase]:
    """
    The owner action limits over the shared counters; the contexts whose
    actions they limit (menu imports, autotests) build it from their own
    edges.
    """

    return Factory(
        AdmitOwnerActionUseCase,
        rate_limit_registry=registries.request_rate_limit_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )


class SpendGuardUseCasesContainer(containers.DeclarativeContainer):
    """
    The spend guard (migration 1142): a business's spend of its day against
    its limits before each model turn and call, the owner actions and API
    requests it limits, the websites allowed to show a chat, and the
    platform's spend for the admin.
    """

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    spend_limit_notices: Singleton[SpendLimitNoticeFacilitator] = Singleton(
        SpendLimitNoticeFacilitator,
        manager_notifier=facilitators.manager_notification_facilitator,
        job_queue=facilitators.job_queue_facilitator,
        localized_text_resolver=utilities.localized_text_resolver,
        alert_settings=config.app_settings.provided.platform_alerts,
    )
    check_business_spend_use_case: Factory[CheckBusinessSpendUseCase] = Factory(
        CheckBusinessSpendUseCase,
        business_limits_repo=repositories.business_limits_repo,
        spend_limit_mark_repo=repositories.spend_limit_mark_repo,
        usage_spend_repo=repositories.usage_spend_repo,
        user_repo=repositories.user_repo,
        audit_log_repo=repositories.audit_log_repo,
        notices=spend_limit_notices,
        exchange_rate_registry=registries.exchange_rate_registry,
        settings=config.app_settings.provided.spend_guard,
    )
    admit_owner_action_use_case: Factory[AdmitOwnerActionUseCase] = (
        admit_owner_action_factory(registries, time_provider)
    )
    admit_api_request_use_case: Factory[AdmitApiRequestUseCase] = Factory(
        AdmitApiRequestUseCase,
        rate_limit_registry=registries.request_rate_limit_registry,
        settings=config.app_settings.provided.spend_guard,
        wall_clock=time_provider.microsecond_wall_clock,
    )
