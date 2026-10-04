from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.platform_use_cases import PlatformUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.platform_admins import (
    AddPlatformAdminCommand,
    ChangePlatformAdminRoleCommand,
    PlatformAdminTeamQuery,
    PlatformAdminTeamView,
    RemovePlatformAdminCommand,
)
from app.schemas.dto.support_access import (
    CloseClientCabinetCommand,
    EndSupportAccessCommand,
    SupportAccessQuery,
    SupportAccessView,
    UpdateSupportWriteAccessCommand,
)
from app.use_cases.admin.access.close_client_cabinet_use_case import (
    CloseClientCabinetUseCase,
)
from app.use_cases.admin.access.end_expired_support_access_use_case import (
    EndExpiredSupportAccessUseCase,
)
from app.use_cases.admin.team.add_platform_admin_use_case import (
    AddPlatformAdminUseCase,
)
from app.use_cases.admin.team.change_platform_admin_role_use_case import (
    ChangePlatformAdminRoleUseCase,
)
from app.use_cases.admin.team.list_platform_admins_use_case import (
    ListPlatformAdminsUseCase,
)
from app.use_cases.admin.team.remove_platform_admin_use_case import (
    RemovePlatformAdminUseCase,
)
from app.use_cases.businesses.support_access.end_support_access_use_case import (
    EndSupportAccessUseCase,
)
from app.use_cases.businesses.support_access.get_support_access_use_case import (
    GetSupportAccessUseCase,
)
from app.use_cases.businesses.support_access.update_support_write_access_use_case import (  # noqa: E501
    UpdateSupportWriteAccessUseCase,
)


class AccessUseCasesContainer(containers.DeclarativeContainer):
    """
    Platform access (1103): the admin team (SUPER admins), a platform
    admin leaving a client's cabinet, the job that ends expired support
    access, and the owner's side of support access (the banner, the consent
    to changes, ending it). SecurityUseCasesContainer extends it.
    """

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    platform_use_cases: PlatformUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- The admin team.
    list_platform_admins_use_case: Factory[
        UseCaseContract[PlatformAdminTeamQuery, PlatformAdminTeamView]
    ] = Factory(
        ListPlatformAdminsUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        platform_admin_repo=repositories.platform_admin_repo,
        user_repo=repositories.user_repo,
    )
    add_platform_admin_use_case: Factory[
        UseCaseContract[AddPlatformAdminCommand, PlatformAdminTeamView]
    ] = Factory(
        AddPlatformAdminUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        platform_admin_repo=repositories.platform_admin_repo,
        user_repo=repositories.user_repo,
        phone_number_parser=utilities.phone_number_parser,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        step_up=utilities.step_up_guard,
    )
    change_platform_admin_role_use_case: Factory[
        UseCaseContract[ChangePlatformAdminRoleCommand, PlatformAdminTeamView]
    ] = Factory(
        ChangePlatformAdminRoleUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        platform_admin_repo=repositories.platform_admin_repo,
        user_repo=repositories.user_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        step_up=utilities.step_up_guard,
    )
    remove_platform_admin_use_case: Factory[
        UseCaseContract[RemovePlatformAdminCommand, None]
    ] = Factory(
        RemovePlatformAdminUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        platform_admin_repo=repositories.platform_admin_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        step_up=utilities.step_up_guard,
    )

    # --- Support access: the admin's side and its expiry.
    close_client_cabinet_use_case: Factory[
        UseCaseContract[CloseClientCabinetCommand, None]
    ] = Factory(
        CloseClientCabinetUseCase,
        authorize_platform_admin=platform_use_cases.authorize_platform_admin_use_case,
        grant_repo=repositories.support_access_grant_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    end_expired_support_access_use_case: Factory[
        UseCaseContract[JobTick, JobReport]
    ] = Factory(
        EndExpiredSupportAccessUseCase,
        grant_repo=repositories.support_access_grant_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )

    # --- Support access: the owner's side.
    get_support_access_use_case: Factory[
        UseCaseContract[SupportAccessQuery, SupportAccessView]
    ] = Factory(
        GetSupportAccessUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        grant_repo=repositories.support_access_grant_repo,
        user_repo=repositories.user_repo,
        platform_admins=registries.platform_admin_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    update_support_write_access_use_case: Factory[
        UseCaseContract[UpdateSupportWriteAccessCommand, SupportAccessView]
    ] = Factory(
        UpdateSupportWriteAccessUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        grant_repo=repositories.support_access_grant_repo,
        audit_log_repo=repositories.audit_log_repo,
        user_repo=repositories.user_repo,
        platform_admins=registries.platform_admin_registry,
        wall_clock=time_provider.microsecond_wall_clock,
        step_up=utilities.step_up_guard,
    )
    end_support_access_use_case: Factory[
        UseCaseContract[EndSupportAccessCommand, None]
    ] = Factory(
        EndSupportAccessUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        grant_repo=repositories.support_access_grant_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
