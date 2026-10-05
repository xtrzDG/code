from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory, Singleton

from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.facilitators.spend_guard.spend_limit_notice_facilitator import (
    SpendLimitNoticeFacilitator,
)
from app.schemas.dto.spend_guard import (
    ApiRequestAdmission,
    OwnerActionAdmission,
    SpendCheckRequest,
    SpendVerdict,
)
from app.schemas.dto.widget_origins import (
    SaveWidgetAllowedOriginsCommand,
    WidgetAllowedOriginsQuery,
    WidgetAllowedOriginsView,
    WidgetOriginCheck,
)
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.use_cases.spend_guard.admit_api_request_use_case import (
    AdmitApiRequestUseCase,
)
from app.use_cases.spend_guard.admit_owner_action_use_case import (
    AdmitOwnerActionUseCase,
)
from app.use_cases.spend_guard.check_business_spend_use_case import (
    CheckBusinessSpendUseCase,
)
from app.use_cases.spend_guard.check_widget_origin_use_case import (
    CheckWidgetOriginUseCase,
)
from app.use_cases.spend_guard.get_widget_allowed_origins_use_case import (
    GetWidgetAllowedOriginsUseCase,
)
from app.use_cases.spend_guard.save_widget_allowed_origins_use_case import (
    SaveWidgetAllowedOriginsUseCase,
)
from app.utilities.spend.widget_origins import platform_page_origins


def admit_owner_action_factory(
    registries: RegistriesContainer, time_provider: TimeProviderContainer
) -> Factory[UseCaseContract[OwnerActionAdmission, None]]:
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
    check_business_spend_use_case: Factory[
        UseCaseContract[SpendCheckRequest, SpendVerdict]
    ] = Factory(
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
    admit_owner_action_use_case: Factory[
        UseCaseContract[OwnerActionAdmission, None]
    ] = admit_owner_action_factory(registries, time_provider)
    admit_api_request_use_case: Factory[UseCaseContract[ApiRequestAdmission, None]] = (
        Factory(
            AdmitApiRequestUseCase,
            rate_limit_registry=registries.request_rate_limit_registry,
            settings=config.app_settings.provided.spend_guard,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    platform_origins: Singleton[list[PublicBaseUrl]] = Singleton(
        platform_page_origins,
        cabinet_base_url=config.app_settings.provided.cabinet_base_url,
        app_base_url=config.app_settings.provided.app_base_url,
        cabinet_origins=config.app_settings.provided.cors_allowed_origins,
    )
    check_widget_origin_use_case: Factory[UseCaseContract[WidgetOriginCheck, None]] = (
        Factory(
            CheckWidgetOriginUseCase,
            business_limits_repo=repositories.business_limits_repo,
            platform_origins=platform_origins,
        )
    )
    get_widget_allowed_origins_use_case: Factory[
        UseCaseContract[WidgetAllowedOriginsQuery, WidgetAllowedOriginsView]
    ] = Factory(
        GetWidgetAllowedOriginsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        business_limits_repo=repositories.business_limits_repo,
        platform_origins=platform_origins,
    )
    save_widget_allowed_origins_use_case: Factory[
        UseCaseContract[SaveWidgetAllowedOriginsCommand, WidgetAllowedOriginsView]
    ] = Factory(
        SaveWidgetAllowedOriginsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        business_limits_repo=repositories.business_limits_repo,
        platform_origins=platform_origins,
        wall_clock=time_provider.microsecond_wall_clock,
    )
